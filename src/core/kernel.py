from typing import List
from core.tarefas import TCB, EstadoTarefa
from core.hardware import Hardware

class Escalonador:
    """Interface abstrata para algoritmos de escalonamento."""
    def eleger(self, fila_prontos: List[TCB], tick_atual: int, tarefas_nas_cpus: List[int]) -> List[TCB]:
        raise NotImplementedError()

    def regra_desempate(self, t: TCB, tick_atual: int, tarefas_nas_cpus: List[int]) -> tuple:
        """Regras de desempate padrão do sistema."""
        executava = 0 if t.id_tarefa in tarefas_nas_cpus else 1
        sorteio = hash((t.id_tarefa, tick_atual))
        return (executava, t.prazo_absoluto_atual, t.instante_ingresso, t.duracao_original, sorteio)

class EscalonadorRM(Escalonador):
    """Rate Monotonic: Maior prioridade para o menor período."""
    def eleger(self, fila_prontos: List[TCB], tick_atual: int, tarefas_nas_cpus: List[int]) -> List[TCB]:
        return sorted(fila_prontos, key=lambda t: (t.periodo, self.regra_desempate(t, tick_atual, tarefas_nas_cpus)))

class EscalonadorEDF(Escalonador):
    """Earliest Deadline First: Maior prioridade para o menor deadline absoluto."""
    def eleger(self, fila_prontos: List[TCB], tick_atual: int, tarefas_nas_cpus: List[int]) -> List[TCB]:
        return sorted(fila_prontos, key=lambda t: (t.prazo_absoluto_atual, self.regra_desempate(t, tick_atual, tarefas_nas_cpus)))

class GerenciadorTarefas:
    """Subsistema do Kernel responsável pelo ciclo de vida e estado das tarefas."""
    def __init__(self, tarefas: List[TCB]):
        self.tarefas_sistema = tarefas

    def obter_elegiveis(self) -> List[TCB]:
        """Retorna tarefas que estão PRONTAS ou na CPU mas passíveis de preempção."""
        return [t for t in self.tarefas_sistema if t.estado == EstadoTarefa.PRONTA and t.execucoes_completadas < 10]

    def atualizar_estados_por_tempo(self, tick_atual: int):
        for t in self.tarefas_sistema:
            # Trava do limite do projeto A
            if t.execucoes_completadas >= 10:
                t.estado = EstadoTarefa.FINALIZADA
                continue

            # Ingressa pela primeira vez
            if t.estado == EstadoTarefa.NOVA and tick_atual >= t.instante_ingresso:
                t.estado = EstadoTarefa.PRONTA
                t.prazo_absoluto_atual = tick_atual + t.prazo_relativo
                t.tempo_ja_executado = 0
                
            # Reativar tarefa periódica
            elif t.estado == EstadoTarefa.FINALIZADA and t.execucoes_completadas < 10:
                proximo_inicio = t.instante_ingresso + (t.execucoes_completadas * t.periodo)
                if tick_atual == proximo_inicio:
                    t.estado = EstadoTarefa.PRONTA
                    t.prazo_absoluto_atual = tick_atual + t.prazo_relativo
                    t.tempo_ja_executado = 0
                    t.sofreu_atraso = False

            # Verifica vencimento de prazo (deadline perdido)
            if t.estado in (EstadoTarefa.PRONTA, EstadoTarefa.EXECUTANDO):
                if tick_atual > t.prazo_absoluto_atual:
                    t.sofreu_atraso = True

    def todas_finalizadas(self) -> bool:
        return all(t.estado == EstadoTarefa.FINALIZADA for t in self.tarefas_sistema)

class Kernel:
    """Núcleo do Sistema Operacional. Orquestra Hardware, Escalonador e Tarefas."""
    def __init__(self, hardware: Hardware, algoritmo: str, tarefas: List[TCB]):
        self.hardware = hardware
        self.gerenciador_tarefas = GerenciadorTarefas(tarefas)
        self.algoritmo = algoritmo.lower()
        if self.algoritmo == 'rm':
            self.escalonador = EscalonadorRM()
        else:
            self.escalonador = EscalonadorEDF()

    def tratar_interrupcao_relogio(self):
        """Disparado a cada ciclo de tempo físico do hardware."""
        # 1. Analisa progresso das tarefas nas CPUs no tick que acabou de passar
        for cpu in self.hardware.cpus:
            if cpu.tarefa_atual:
                t = cpu.tarefa_atual
                t.tempo_ja_executado += 1
                if t.tempo_ja_executado >= t.duracao_original:
                    t.estado = EstadoTarefa.FINALIZADA
                    t.execucoes_completadas += 1
                    cpu.tarefa_atual = None
                else:
                    t.estado = EstadoTarefa.PRONTA

        # 2. Registra avanço do tempo físico
        self.hardware.relogio.tick_atual += 1
        tick = self.hardware.relogio.tick_atual

        # 3. Gerenciador acorda tarefas ou pune por atraso
        self.gerenciador_tarefas.atualizar_estados_por_tempo(tick)

        # 4. Escalonador julga prioridades
        elegiveis = self.gerenciador_tarefas.obter_elegiveis()
        ids_nas_cpus = [cpu.tarefa_atual.id_tarefa for cpu in self.hardware.cpus if cpu.tarefa_atual]
        fila_prontos = self.escalonador.eleger(elegiveis, tick, ids_nas_cpus)

        # 5. Despachante (Dispatcher) distribui as CPUs
        for cpu in self.hardware.cpus:
            cpu.tarefa_atual = None
            
        for cpu in self.hardware.cpus:
            if fila_prontos:
                t = fila_prontos.pop(0)
                t.estado = EstadoTarefa.EXECUTANDO
                t.id_cpu_alocada = cpu.id_cpu
                cpu.tarefa_atual = t
            else:
                cpu.tempo_desligado += 1

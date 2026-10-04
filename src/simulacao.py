import copy
from typing import List, Optional
from modelos import EstadoSistema, EstadoTarefa, Processador, BlocoControleTarefa
from escalonador import ProtocoloEscalonador
from historico import GerenciadorHistorico

def avancar_um_tick(estado_anterior: EstadoSistema, escalonador: ProtocoloEscalonador) -> EstadoSistema:
    """
    Avança a simulação em exato 1 tick, baseando-se no estado anterior (cópia profunda).
    """
    novo_estado = copy.deepcopy(estado_anterior)
    
    # 1. Atualizar tarefas que estavam executando
    for cpu in novo_estado.cpus:
        if cpu.tarefa_atual:
            t = cpu.tarefa_atual
            t.tempo_ja_executado += 1
            if t.tempo_ja_executado >= t.duracao_original:
                t.estado = EstadoTarefa.FINALIZADA
                t.execucoes_completadas += 1
                cpu.tarefa_atual = None
            else:
                # Voltar para PRONTA para permitir preempção
                t.estado = EstadoTarefa.PRONTA

    # O tick avança DEPOIS de processar o tempo gasto no tick anterior
    novo_estado.tick_atual += 1

    # 2. Ativar novas ocorrências (periódicas) ou novas tarefas (ingresso)
    _ativar_tarefas_periodicas(novo_estado)
    
    # 3. Verificar vencimento de prazos
    _verificar_vencimento_prazos(novo_estado)
    
    # 4. Coletar tarefas prontas (já incluem as preemptadas que voltaram para PRONTA)
    tarefas_elegiveis = [t for t in novo_estado.tarefas if t.estado == EstadoTarefa.PRONTA and t.execucoes_completadas < 10]
    
    # Lista de IDs das tarefas que já estavam nas CPUs antes do escalonador agir (para desempate)
    # Na verdade, precisamos saber quais estavam rodando no tick_anterior. 
    # Podemos olhar no estado_anterior para ver quem estava alocado.
    ids_em_execucao = [cpu.tarefa_atual.id_tarefa for cpu in estado_anterior.cpus if cpu.tarefa_atual]
    
    # 5. Ordenar tarefas usando o escalonador e as regras de desempate
    fila_ordenada = escalonador(tarefas_elegiveis, novo_estado.tick_atual, ids_em_execucao)
    
    # 6. Distribuir nas CPUs
    _distribuir_tarefas_nas_cpus(novo_estado, fila_ordenada)
    
    # 7. Contabilizar desligamentos
    _desligar_cpus_ociosas(novo_estado)
    
    return novo_estado

def _ativar_tarefas_periodicas(estado: EstadoSistema):
    for t in estado.tarefas:
        if t.execucoes_completadas >= 10:
            t.estado = EstadoTarefa.FINALIZADA
            continue

        # Ingressa pela primeira vez
        if t.estado == EstadoTarefa.NOVA and estado.tick_atual >= t.instante_ingresso:
            t.estado = EstadoTarefa.PRONTA
            t.prazo_absoluto_atual = estado.tick_atual + t.prazo_relativo
            t.tempo_ja_executado = 0
            
        # Reativar tarefa periódica
        elif t.estado == EstadoTarefa.FINALIZADA and t.execucoes_completadas < 10:
            proximo_inicio = t.instante_ingresso + (t.execucoes_completadas * t.periodo)
            if estado.tick_atual == proximo_inicio:
                t.estado = EstadoTarefa.PRONTA
                t.prazo_absoluto_atual = estado.tick_atual + t.prazo_relativo
                t.tempo_ja_executado = 0
                t.sofreu_atraso = False

def _verificar_vencimento_prazos(estado: EstadoSistema):
    for t in estado.tarefas:
        if t.estado in (EstadoTarefa.PRONTA, EstadoTarefa.EXECUTANDO):
            if estado.tick_atual > t.prazo_absoluto_atual:
                t.sofreu_atraso = True

def _distribuir_tarefas_nas_cpus(estado: EstadoSistema, fila_ordenada: list):
    # Esvaziar cpus primeiro
    for cpu in estado.cpus:
        cpu.tarefa_atual = None
        
    for cpu in estado.cpus:
        if fila_ordenada:
            t = fila_ordenada.pop(0)
            t.estado = EstadoTarefa.EXECUTANDO
            t.id_cpu_alocada = cpu.id_cpu
            cpu.tarefa_atual = t
            
def _desligar_cpus_ociosas(estado: EstadoSistema):
    for cpu in estado.cpus:
        if not cpu.tarefa_atual:
            cpu.tempo_desligado += 1

def estado_finalizado(estado: EstadoSistema) -> bool:
    """Verifica se a simulação chegou ao fim (todas as tarefas estão finalizadas)."""
    return all(t.estado == EstadoTarefa.FINALIZADA for t in estado.tarefas)

def executar_simulacao_completa(historico: GerenciadorHistorico, escalonador: ProtocoloEscalonador, max_ticks: int = 5000) -> bool:
    """
    Avança a simulação automaticamente até que todas as tarefas terminem ou o limite de ticks seja atingido.
    Retorna True se finalizou normalmente, False se excedeu o limite de segurança.
    """
    count = 0
    while True:
        count += 1
        if count > max_ticks:
            return False # Estourou a trava de segurança
            
        est = historico.estado_atual
        if estado_finalizado(est):
            return True
            
        novo_est = avancar_um_tick(est, escalonador)
        historico.avancar(novo_est)

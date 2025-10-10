import streamlit as st

# --- Configurações Iniciais ---
st.set_page_config(page_title="Gerenciador de Tarefas Simples", layout="centered")
st.title("📋 Meu Gerenciador de Tarefas")
st.markdown("---")

# Inicializa a lista de tarefas na 'session_state' se ainda não existir
if 'tasks' not in st.session_state:
    st.session_state['tasks'] = []

# --- Funções de Gerenciamento de Tarefas ---

def add_task(new_task_text):
    """Adiciona uma nova tarefa à lista."""
    if new_task_text: # Garante que o texto não está vazio
        # A tarefa é um dicionário: {'name': str, 'done': bool}
        st.session_state['tasks'].append({'name': new_task_text, 'done': False})

def toggle_task_done(task_index):
    """Alterna o estado de 'concluída' de uma tarefa."""
    # Acessa a tarefa pelo índice e inverte o valor de 'done'
    st.session_state['tasks'][task_index]['done'] = not st.session_state['tasks'][task_index]['done']

def delete_task(task_index):
    """Remove uma tarefa da lista."""
    # Remove a tarefa da lista usando o índice
    st.session_state['tasks'].pop(task_index)

# --- Entrada de Nova Tarefa ---

st.header("Adicionar Nova Tarefa")

# Cria um formulário (form) para melhor controle do input
with st.form(key='add_task_form', clear_on_submit=True):
    # Campo de texto para a nova tarefa
    new_task = st.text_input("Descrição da Tarefa", key="new_task_text", label_visibility="collapsed")
    
    # Botão para submeter o formulário
    submit_button = st.form_submit_button(label='Adicionar Tarefa')

    if submit_button:
        # Chama a função para adicionar a tarefa ao clicar no botão
        add_task(new_task)
        # Linha st.experimental_rerun() REMOVIDA para corrigir o erro! 
        # O Streamlit irá reroduzir o código automaticamente.


# --- Exibição e Gerenciamento da Lista de Tarefas ---

st.markdown("---")
st.header("📝 Lista de Tarefas")

if not st.session_state['tasks']:
    st.info("Sua lista de tarefas está vazia! Adicione algo para começar.")
else:
    # Itera sobre a lista de tarefas e exibe cada uma
    for i, task in enumerate(st.session_state['tasks']):
        
        # Usa colunas para alinhar os elementos (checkbox, nome e botão de exclusão)
        col1, col2, col3 = st.columns([1, 6, 1])

        # Coluna 1: Checkbox para Marcar como Concluída
        with col1:
            # O 'key' é crucial para identificar o widget no Streamlit
            st.checkbox(
                "", 
                value=task['done'], 
                key=f"check_{i}",
                # Chama a função ao clicar no checkbox
                on_change=toggle_task_done, 
                args=(i,),
                label_visibility="collapsed"
            )

        # Coluna 2: Nome da Tarefa (com formatação)
        with col2:
            task_display = f"~~{task['name']}~~" if task['done'] else task['name']
            # Exibe o nome da tarefa
            st.write(task_display)

        # Coluna 3: Botão de Excluir
        with col3:
            # O 'key' é crucial para identificar o widget no Streamlit
            st.button(
                "❌", 
                key=f"delete_{i}", 
                # Chama a função ao clicar no botão
                on_click=delete_task, 
                args=(i,)
            )

st.markdown("---")

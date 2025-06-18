# Sistema de Controle Dinâmico Moderno

## Descrição
Este aplicativo em Python, com interface gráfica desenvolvida em PyQt6, permite a leitura, visualização e registro de dados provenientes de um Arduino via porta serial. Ele é voltado para experimentos e monitoramento de sistemas de controle, facilitando a análise de variáveis como temperatura, setpoint, erro e saída.

## Funcionalidades
- **Leitura automática da porta serial** (configurável via interface)
- **Displays digitais** para visualização em tempo real de Temperatura, Setpoint, Erro e Saída
- **Dois gráficos dinâmicos**:
  - Temperatura x Setpoint
  - Saída x Erro
- **Ajuste manual dos eixos** dos gráficos (X e Y, incluindo Y mínimo para o gráfico 1)
- **Botões para limpar e exportar gráficos** (PNG)
- **Registro dos dados em arquivo CSV** (iniciado/parado por botão)
- **Indicador visual de gravação** (círculo verde claro/escuro)
- **Seleção e atualização de portas COM** (botão e ComboBox)
- **Botão para conectar/desconectar a porta serial**
- **Tema escuro moderno** para melhor visualização

## Como usar
1. **Execute o aplicativo** (via Python ou executável gerado).
2. **Selecione a porta COM** desejada (use "Atualizar COMs" para buscar novas portas).
3. Clique em **Conectar** para iniciar a leitura da porta selecionada.
4. Os valores lidos aparecerão nos displays e gráficos em tempo real.
5. Para gravar os dados, clique em **Escolher Arquivo** e depois em **Iniciar Leitura**.
6. Para parar a gravação, clique em **Parar Leitura**.
7. Ajuste os eixos dos gráficos conforme necessário e utilize os botões para limpar ou exportar as visualizações.

## Requisitos
- Windows 10/11
- Python 3.12+
- Bibliotecas: pyqt6, pyserial, pandas, matplotlib, pyinstaller (para gerar executável)

## Instalação de dependências
No terminal, execute:
```
pip install pyqt6 pyserial pandas matplotlib
```

## Geração do executável
Com o ambiente virtual ativado, execute:
```
pyinstaller --noconfirm --onefile --windowed main.py
```
O executável será criado na pasta `dist`.

## Observações
- O aplicativo detecta automaticamente as portas COM disponíveis.
- O filtro passa-baixa de 1ª ordem (5s) é aplicado aos dados antes da exibição e gravação.
- Os gráficos podem ser limpos individualmente e reiniciam o tempo do eixo X ao serem limpos.
- O tema escuro é aplicado globalmente para conforto visual.

## Suporte
Para dúvidas, sugestões ou problemas, entre em contato com o responsável pelo projeto ou abra uma issue no repositório compartilhado.

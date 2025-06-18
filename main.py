"""
main.py - Sistema de Controle Dinâmico Moderno

Aplicativo PyQt6 para leitura, visualização e registro de dados de um Arduino via porta serial.
Inclui displays digitais, gráficos dinâmicos, gravação em CSV, seleção de porta COM e tema escuro.
"""

import sys
import csv
import re
import threading
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QLCDNumber, QComboBox
)
from PyQt6.QtCore import QTimer
import time
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QLineEdit, QGroupBox, QSizePolicy
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor

class SerialReader(threading.Thread):
    """
    Thread para leitura assíncrona da porta serial.
    Chama o callback fornecido a cada linha lida.
    """
    def __init__(self, port, baudrate, callback):
        """
        Inicializa a thread de leitura serial.
        Args:
            port (str): Porta serial (ex: 'COM3')
            baudrate (int): Baudrate da comunicação
            callback (callable): Função chamada a cada linha lida
        """
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.callback = callback
        self._stop_event = threading.Event()
        self.ser = None

    def run(self):
        """
        Executa a leitura contínua da porta serial até ser interrompida.
        """
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            while not self._stop_event.is_set():
                line = self.ser.readline().decode(errors='ignore').strip()
                if line:
                    self.callback(line)
        except Exception as e:
            print(f"Erro na leitura serial: {e}")
        finally:
            if self.ser:
                self.ser.close()

    def stop(self):
        """
        Solicita a parada da thread.
        """
        self._stop_event.set()

class PlotWidget(FigureCanvas):
    """
    Widget de gráfico dinâmico usando matplotlib integrado ao PyQt6.
    Permite atualização, limpeza, exportação e ajuste de eixos.
    """
    def __init__(self, parent=None, title='', ylabel='', color1='b', color2='r'):
        """
        Inicializa o gráfico.
        Args:
            parent: Widget pai
            title (str): Título do gráfico
            ylabel (str): Rótulo do eixo Y
            color1 (str): Cor da primeira linha
            color2 (str): Cor da segunda linha
        """
        self.fig = Figure(figsize=(4,2.5))
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title(title)
        self.ax.set_xlabel('Tempo (min)')
        self.ax.set_ylabel(ylabel)
        self.line1, = self.ax.plot([], [], color1, label='')
        self.line2, = self.ax.plot([], [], color2, label='')
        self.ax.legend()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.fig.tight_layout()
        self.xdata = []
        self.ydata1 = []
        self.ydata2 = []
        self.xlim = 2
        self.ylim_min = 0
        self.ylim_max = 100
        self.ax.set_xlim(0, self.xlim)
        self.ax.set_ylim(self.ylim_min, self.ylim_max)
        self.t0 = time.time()

    def update_plot(self, x, y1, y2):
        """
        Atualiza o gráfico com novos dados.
        Args:
            x (float): Valor do eixo X (tempo em minutos)
            y1 (float): Valor da primeira variável
            y2 (float): Valor da segunda variável
        """
        self.xdata.append(x)
        self.ydata1.append(y1)
        self.ydata2.append(y2)
        self.line1.set_data(self.xdata, self.ydata1)
        self.line2.set_data(self.xdata, self.ydata2)
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.set_xlim(0, self.xlim)
        self.ax.set_ylim(self.ylim_min, self.ylim_max)
        self.draw()

    def clear_plot(self):
        """
        Limpa o gráfico e reinicia o tempo inicial (t0).
        """
        self.xdata.clear()
        self.ydata1.clear()
        self.ydata2.clear()
        self.line1.set_data([], [])
        self.line2.set_data([], [])
        self.t0 = time.time()
        self.draw()

    def export_png(self, filename):
        """
        Exporta o gráfico atual para um arquivo PNG.
        Args:
            filename (str): Caminho do arquivo PNG
        """
        self.fig.savefig(filename)

    def set_axes(self, xlim, ylim_max, ylim_min=0):
        """
        Ajusta os limites dos eixos X e Y do gráfico.
        Args:
            xlim (float): Limite máximo do eixo X
            ylim_max (float): Limite máximo do eixo Y
            ylim_min (float): Limite mínimo do eixo Y (default=0)
        """
        self.xlim = xlim
        self.ylim_min = ylim_min
        self.ylim_max = ylim_max
        self.ax.set_xlim(0, self.xlim)
        self.ax.set_ylim(self.ylim_min, self.ylim_max)
        self.draw()

class StatusCircle(QWidget):
    """
    Widget indicador de status (círculo verde) para mostrar se a gravação do CSV está ativa.
    """
    def __init__(self, parent=None):
        """
        Inicializa o círculo de status.
        """
        super().__init__(parent)
        self.active = False
        self.setFixedSize(24, 24)

    def set_active(self, active: bool):
        """
        Atualiza o status do círculo (ativo/inativo).
        Args:
            active (bool): True para ativo (verde claro), False para inativo (verde escuro)
        """
        self.active = active
        self.update()

    def paintEvent(self, event):
        """
        Desenha o círculo com a cor correspondente ao status.
        """
        painter = QPainter(self)
        color = QColor(0, 180, 0) if self.active else QColor(0, 80, 0)
        painter.setBrush(color)
        painter.setPen(QColor(0, 60, 0))
        painter.drawEllipse(2, 2, 20, 20)

class MainWindow(QWidget):
    """
    Janela principal do aplicativo de leitura e visualização de dados do Arduino.
    Gerencia interface, leitura serial, gráficos, gravação em CSV e seleção de porta COM.
    """
    def __init__(self):
        """
        Inicializa a janela principal e todos os widgets/componentes.
        """
        super().__init__()
        self.setWindowTitle('Leitor Serial Arduino')
        self.setFixedSize(900, 900)
        self.serial_thread = None
        self.csv_file = None
        self.csv_writer = None
        self.file_name = 'dados.csv'
        self.port = 'COM4'  # Altere conforme necessário
        self.baudrate = 9600
        self.init_ui()
        self.data = {'T': 0.0, 'SP': 0.0, 'Erro': 0.0, 'Saida': 0.0}
        self.data_filt = {'T': 0.0, 'SP': 0.0, 'Erro': 0.0, 'Saida': 0.0}
        self.last_update = None
        self.t0 = time.time()
        # Inicia a leitura serial automaticamente ao abrir o app
        self.serial_thread = SerialReader(self.port, self.baudrate, self.handle_serial_data)
        self.serial_thread.start()

    def init_ui(self):
        """
        Monta toda a interface gráfica do aplicativo, layouts, botões, displays, gráficos e conexões de sinais.
        """
        from PyQt6.QtWidgets import QFormLayout, QHBoxLayout, QVBoxLayout, QLabel, QGroupBox, QLineEdit, QPushButton
        layout = QVBoxLayout()
        # Linha displays T e SP
        row1 = QHBoxLayout()
        row1.addWidget(QLabel('T (°C)'))
        self.lcd_T = QLCDNumber(); self.lcd_T.setDigitCount(6)
        self.lcd_T.setStyleSheet('background: black;')
        self.lcd_T.setSegmentStyle(QLCDNumber.SegmentStyle.Filled)
        self.lcd_T.setPalette(self.get_orange_palette())
        row1.addWidget(self.lcd_T)
        row1.addWidget(QLabel('SP (°C)'))
        self.lcd_SP = QLCDNumber(); self.lcd_SP.setDigitCount(6)
        self.lcd_SP.setStyleSheet('background: black;')
        self.lcd_SP.setSegmentStyle(QLCDNumber.SegmentStyle.Filled)
        self.lcd_SP.setPalette(self.get_orange_palette())
        row1.addWidget(self.lcd_SP)
        layout.addLayout(row1)
        # Linha displays Erro e Saída
        row2 = QHBoxLayout()
        row2.addWidget(QLabel('Erro (V)'))
        self.lcd_Erro = QLCDNumber(); self.lcd_Erro.setDigitCount(6)
        self.lcd_Erro.setStyleSheet('background: black;')
        self.lcd_Erro.setSegmentStyle(QLCDNumber.SegmentStyle.Filled)
        self.lcd_Erro.setPalette(self.get_orange_palette())
        row2.addWidget(self.lcd_Erro)
        row2.addWidget(QLabel('Saída (V)'))
        self.lcd_Saida = QLCDNumber(); self.lcd_Saida.setDigitCount(6)
        self.lcd_Saida.setStyleSheet('background: black;')
        self.lcd_Saida.setSegmentStyle(QLCDNumber.SegmentStyle.Filled)
        self.lcd_Saida.setPalette(self.get_orange_palette())
        row2.addWidget(self.lcd_Saida)
        layout.addLayout(row2)
        # Gráfico 1
        self.plot1 = PlotWidget(title='Temperatura e Setpoint', ylabel='Temperatura (°C)', color1='b', color2='g')
        self.plot1.set_axes(10, 60)
        self.plot1.line1.set_label('T (°C)')
        self.plot1.line2.set_label('SP (°C)')
        self.plot1.ax.legend()
        gbox1 = QGroupBox('Temperatura x Setpoint')
        v1 = QVBoxLayout(); v1.addWidget(self.plot1)
        # Inputs e botões na mesma linha para gráfico 1
        row_g1 = QHBoxLayout()
        self.xlim_input1 = QLineEdit('10')
        self.ylim_ini_input1 = QLineEdit('20')  # Novo input para Y inicial
        self.ylim_input1 = QLineEdit('60')
        row_g1.addWidget(QLabel('X (min):'))
        row_g1.addWidget(self.xlim_input1)
        row_g1.addWidget(QLabel('Y inicial (°C):'))
        row_g1.addWidget(self.ylim_ini_input1)
        row_g1.addWidget(QLabel('Y final (°C):'))
        row_g1.addWidget(self.ylim_input1)
        self.btn_axes1 = QPushButton('Ajustar Eixos')
        self.btn_clear1 = QPushButton('Limpar Gráfico')
        self.btn_export1 = QPushButton('Exportar Gráfico')
        row_g1.addWidget(self.btn_axes1)
        row_g1.addWidget(self.btn_clear1)
        row_g1.addWidget(self.btn_export1)
        v1.addLayout(row_g1)
        gbox1.setLayout(v1)
        layout.addWidget(gbox1)
        # Gráfico 2
        self.plot2 = PlotWidget(title='Saída e Erro', ylabel='Tensão (V)', color1='r', color2='m')
        self.plot2.set_axes(10, 6)
        self.plot2.line1.set_label('Saída (V)')
        self.plot2.line2.set_label('Erro (V)')
        self.plot2.ax.legend()
        gbox2 = QGroupBox('Saída x Erro')
        v2 = QVBoxLayout(); v2.addWidget(self.plot2)
        row_g2 = QHBoxLayout()
        self.xlim_input2 = QLineEdit('10'); self.ylim_input2 = QLineEdit('6')
        row_g2.addWidget(QLabel('X (min):'))
        row_g2.addWidget(self.xlim_input2)
        row_g2.addWidget(QLabel('Y (V):'))
        row_g2.addWidget(self.ylim_input2)
        self.btn_axes2 = QPushButton('Ajustar Eixos')
        self.btn_clear2 = QPushButton('Limpar Gráfico')
        self.btn_export2 = QPushButton('Exportar Gráfico')
        row_g2.addWidget(self.btn_axes2)
        row_g2.addWidget(self.btn_clear2)
        row_g2.addWidget(self.btn_export2)
        v2.addLayout(row_g2)
        gbox2.setLayout(v2)
        layout.addWidget(gbox2)
        # Botões principais
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton('Iniciar Leitura')
        self.btn_stop = QPushButton('Parar Leitura')
        self.btn_file = QPushButton('Escolher Arquivo')
        self.btn_update_com = QPushButton('Atualizar COMs')
        self.combobox_com = QComboBox()
        self.combobox_com.setMinimumWidth(90)
        self.update_com_ports()
        self.combobox_com.currentTextChanged.connect(self.on_com_selected)
        self.btn_update_com.clicked.connect(self.update_com_ports)
        self.btn_connect_com = QPushButton('Conectar')
        self.btn_connect_com.clicked.connect(self.connect_com_port)
        self.status_circle = StatusCircle()
        self.btn_start.clicked.connect(self.start_reading)
        self.btn_stop.clicked.connect(self.stop_reading)
        self.btn_file.clicked.connect(self.choose_file)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_file)
        btn_layout.addWidget(self.btn_update_com)
        btn_layout.addWidget(self.combobox_com)
        btn_layout.addWidget(self.btn_connect_com)
        btn_layout.addWidget(self.status_circle)
        layout.addLayout(btn_layout)
        # Status da gravação em arquivo CSV
        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_displays)
        self.timer.start(200)

        self.btn_axes1.clicked.connect(lambda: self.set_axes(self.plot1, self.xlim_input1, self.ylim_input1, self.ylim_ini_input1))
        self.btn_axes2.clicked.connect(lambda: self.set_axes(self.plot2, self.xlim_input2, self.ylim_input2))
        self.btn_export1.clicked.connect(lambda: self.export_plot(self.plot1))
        self.btn_export2.clicked.connect(lambda: self.export_plot(self.plot2))
        self.btn_clear1.clicked.connect(self.plot1.clear_plot)
        self.btn_clear2.clicked.connect(self.plot2.clear_plot)
        self.apply_dark_theme()

    def choose_file(self):
        """
        Abre diálogo para o usuário escolher o arquivo CSV de gravação.
        """
        file, _ = QFileDialog.getSaveFileName(self, 'Escolher arquivo CSV', '', 'CSV Files (*.csv)')
        if file:
            self.file_name = file

    def start_reading(self):
        """
        Inicia a gravação dos dados lidos em um arquivo CSV.
        """
        # Apenas abre o arquivo e ativa a escrita, sem iniciar a thread
        if self.csv_file:
            return  # já está gravando
        if self.file_name:
            self.csv_file = open(self.file_name, 'a', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(['T', 'SP', 'Erro', 'Saida'])
            self.status_circle.set_active(True)
        else:
            self.csv_writer = None
            self.status_circle.set_active(False)

    def stop_reading(self):
        """
        Encerra a gravação dos dados no arquivo CSV.
        """
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
        self.csv_writer = None
        self.status_circle.set_active(False)  # Desativa o círculo de status

    def filtro_passa_baixa(self, novo_valor, valor_filtrado_ant, dt, tau):
        """
        Aplica filtro passa-baixa de primeira ordem ao valor lido.
        Args:
            novo_valor (float): Valor atual lido
            valor_filtrado_ant (float): Valor filtrado anterior
            dt (float): Intervalo de tempo desde a última leitura
            tau (float): Constante de tempo do filtro
        Returns:
            float: Valor filtrado
        """
        # Filtro passa-baixa de primeira ordem: y[n] = y[n-1] + (dt/tau)*(x[n] - y[n-1])
        alpha = dt / tau
        return valor_filtrado_ant + alpha * (novo_valor - valor_filtrado_ant)

    def handle_serial_data(self, line):
        """
        Processa cada linha recebida da serial, aplica filtro, atualiza displays, gráficos e gravação.
        Args:
            line (str): Linha recebida da serial
        """
        # Exemplo: T(°C)=48.9 SP(°C)=50.3 Erro(V)=0.01 Saida(V)=2.93
        match = re.match(r'T\(°C\)=(\d+\.\d+) SP\(°C\)=(\d+\.\d+) Erro\(V\)=(\-?\d+\.\d+) Saida\(V\)=(\-?\d+\.\d+)', line)
        if match:
            t, sp, erro, saida = map(float, match.groups())
            self.data = {'T': t, 'SP': sp, 'Erro': erro, 'Saida': saida}
            # Filtro passa-baixa
            now = time.time()
            if self.last_update is None:
                dt = 0.2  # valor inicial (200ms)
            else:
                dt = now - self.last_update
            self.last_update = now
            tau = 5.0  # constante de tempo do filtro (5s)
            for k in self.data:
                self.data_filt[k] = self.filtro_passa_baixa(self.data[k], self.data_filt[k], dt, tau)
            # Atualiza gráficos com tempo relativo a cada gráfico
            tmin1 = (now - self.plot1.t0) / 60.0
            tmin2 = (now - self.plot2.t0) / 60.0
            self.plot1.update_plot(tmin1, self.data_filt['T'], self.data_filt['SP'])
            self.plot2.update_plot(tmin2, self.data_filt['Saida'], self.data_filt['Erro'])
            # Só grava se o arquivo estiver aberto
            if self.csv_writer:
                self.csv_writer.writerow([
                    self.data_filt['T'],
                    self.data_filt['SP'],
                    self.data_filt['Erro'],
                    self.data_filt['Saida']
                ])

    def update_displays(self):
        """
        Atualiza os displays digitais com os valores filtrados mais recentes.
        """
        self.lcd_T.display(f'{self.data_filt["T"]:.1f}')
        self.lcd_SP.display(f'{self.data_filt["SP"]:.1f}')
        self.lcd_Erro.display(f'{self.data_filt["Erro"]:.1f}')
        self.lcd_Saida.display(f'{self.data_filt["Saida"]:.1f}')

    def set_axes(self, plot, x_input, y_input, y_ini_input=None):
        """
        Ajusta os eixos do gráfico conforme os valores dos inputs da interface.
        """
        try:
            xlim = float(x_input.text())
            ylim = float(y_input.text())
            if y_ini_input is not None:
                ylim_ini = float(y_ini_input.text())
                plot.set_axes(xlim, ylim, ylim_ini)
            else:
                plot.set_axes(xlim, ylim)
        except Exception:
            pass

    def export_plot(self, plot):
        """
        Exporta o gráfico selecionado para um arquivo PNG.
        """
        file, _ = QFileDialog.getSaveFileName(self, 'Salvar gráfico como PNG', '', 'PNG Files (*.png)')
        if file:
            plot.export_png(file)

    def closeEvent(self, event):
        """
        Garante o encerramento correto da thread serial e do arquivo CSV ao fechar a janela.
        """
        # Para a thread serial corretamente ao fechar a janela
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.join()
            self.serial_thread = None
        self.stop_reading()
        event.accept()
        self.btn_axes1.clicked.connect(lambda: self.set_axes(self.plot1, self.xlim_input1, self.ylim_input1, self.ylim_ini_input1))
        self.btn_axes2.clicked.connect(lambda: self.set_axes(self.plot2, self.xlim_input2, self.ylim_input2))

    def get_orange_palette(self):
        """
        Retorna uma paleta laranja para os displays digitais.
        """
        from PyQt6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 140, 0))
        palette.setColor(QPalette.ColorRole.Light, QColor(255, 200, 100))
        palette.setColor(QPalette.ColorRole.Dark, QColor(255, 100, 0))
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        return palette

    def apply_dark_theme(self):
        """
        Aplica tema escuro global e estilos modernos à interface.
        """
        from PyQt6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        self.setStyleSheet('''
            QPushButton {
                background-color: #222;
                color: #fff;
                border-radius: 8px;
                padding: 6px 16px;
                border: 1px solid #444;
            }
            QPushButton:hover {
                background-color: #333;
                border: 1px solid #00c896;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 15px;
            }
            QGroupBox {
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #00c896;
                font-weight: bold;
            }
            QLineEdit {
                background: #222;
                color: #fff;
                border-radius: 6px;
                border: 1px solid #444;
                padding: 2px 6px;
            }
            QLCDNumber {
                border-radius: 8px;
                border: 1px solid #444;
                background: #111;
            }
        ''')

    def update_com_ports(self):
        """
        Atualiza a lista de portas COM disponíveis no ComboBox.
        """
        ports = serial.tools.list_ports.comports()
        self.combobox_com.clear()
        for port in ports:
            self.combobox_com.addItem(port.device)
        # Seleciona a porta atual, se existir
        idx = self.combobox_com.findText(self.port)
        if idx >= 0:
            self.combobox_com.setCurrentIndex(idx)

    def on_com_selected(self, text):
        """
        Atualiza a porta COM selecionada pelo usuário.
        """
        self.port = text

    def connect_com_port(self):
        """
        Conecta à porta COM selecionada, reiniciando a thread de leitura serial.
        """
        # Para a thread serial atual, se existir
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.join()
            self.serial_thread = None
        # Atualiza a porta para a selecionada
        self.port = self.combobox_com.currentText()
        # Inicia nova thread serial
        self.serial_thread = SerialReader(self.port, self.baudrate, self.handle_serial_data)
        self.serial_thread.start()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

void setup() {
  Serial.begin(9600);
}

void loop() {
  // Leitura das entradas analógicas
  int rawTemp = analogRead(A3); // LM35
  int rawRef = analogRead(A1);  // Sinal de referência
  int rawOut = analogRead(A2);  // Saída do controlador PI

  // Conversão para tensão (0-5V)
  float voltageTemp = (rawTemp / 1023.0) * 5.0;
  float voltageRef = (rawRef / 1023.0) * 5.0;
  float voltageOut = (rawOut / 1023.0) * 5.0;

  // Cálculo da temperatura (LM35: 10mV/°C)
  float temperature = voltageTemp * 100.0;

  // Cálculo do setpoint (assumindo mesma escala do LM35)
  float setpoint = voltageRef * 100.0;

  // Cálculo do erro em volts
  float error = setpoint - temperature;

  // Impressão dos valores na saída serial
  Serial.print("T(°C)=");
  Serial.print(temperature, 1);
  Serial.print(" SP(°C)=");
  Serial.print(setpoint, 1);
  Serial.print(" Erro(V)=");
  Serial.print(error, 2);
  Serial.print(" Saida(V)=");
  Serial.print(voltageOut, 2);
  Serial.print("\r\n");
  // Aguarda 5 segundos
  delay(1000);
}
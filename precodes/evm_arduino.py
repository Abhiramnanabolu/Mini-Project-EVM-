// Define pins for the buttons
const int party1Button = 2;
const int party2Button = 3;
const int party3Button = 4;

void setup() {
  // Start serial communication
  Serial.begin(9600);

  // Set button pins as inputs with pull-up resistors
  pinMode(party1Button, INPUT_PULLUP);
  pinMode(party2Button, INPUT_PULLUP);
  pinMode(party3Button, INPUT_PULLUP);
}

void loop() {
  // Check button states and send corresponding vote
  if (digitalRead(party1Button) == LOW) {
    Serial.println("1");  // Party 1 voted
    delay(500);  // Debounce delay
  }

  if (digitalRead(party2Button) == LOW) {
    Serial.println("2");  // Party 2 voted
    delay(500);  // Debounce delay
  }

  if (digitalRead(party3Button) == LOW) {
    Serial.println("3");  // Party 3 voted
    delay(500);  // Debounce delay
  }
}

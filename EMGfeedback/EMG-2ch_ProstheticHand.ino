/*
  Simple two EMG channel 1 DoF controller, Bionic and Rehabilitation Engineering at Aalto University
*/
#include <Wire.h>
#include <Adafruit_MotorShield.h>

// These constants won't change. They're used to give names to the pins used:
const int EMGpin1 = A0;       // Analog input pin that the EMG1 is attached to
const int EMGpin2 = A1;       // Analog input pin that the EMG1 is attached to

// Create the motor shield object with the default I2C address
Adafruit_MotorShield AFMS = Adafruit_MotorShield();
// Or, create it with a different I2C address (say for stacking)
// Adafruit_MotorShield AFMS = Adafruit_MotorShield(0x61);

// Select which 'port' M1, M2, M3 or M4. In this case, M1
Adafruit_DCMotor *myMotor = AFMS.getMotor(1);
// You can also make another motor on port M2
//Adafruit_DCMotor *myOtherMotor = AFMS.getMotor(2);

// Running variables
int EMGread1 = 0;           // raw read from the EMG1 sensor
int EMGread2 = 0;           // raw read from the EMG1 sensor

int EMGvalue1 = 0;          // scaled value of the EMG1
int EMGvalue2 = 0;          // scaled value of the EMG2
/*int EMGctrl = 0;            // This is an actual ctrl signal extracted from EMG as EMGctrl=EMGvalue1-EMGvalue2

int buffSize = 2;           // size of the smoothing
int EMGbuffer[2];           // it will act as a moving average filter of buffSize points to smooth the jitter
int total = 0;              // sumation for the moving average
int buffIdx = 0;            // index of the smoothing bugffer

int motorValue = 0;         // value output to the hand (analog out)
int motorValueDummy = 0;    // debugging to be commented out value output to the hand (analog out)*/

void setup() {
  // initialize serial communications at 9600 bps:
  Serial.begin(9600);

  AFMS.begin();             // create with the default frequency 1.6KHz
  //AFMS.begin(1000);       // OR with a different frequency, say 1KHz

  // Set the starting motor speed, from 0 (off) to 255 (max speed)
  myMotor->setSpeed(150);
  myMotor->run(FORWARD);    // turn on motor
  myMotor->run(RELEASE);
}

void loop() {
  // read the raw EMG value:
  EMGread1 = analogRead(EMGpin1);
  EMGread2 = analogRead(EMGpin2);

  // map it to the range of the analog out:
  EMGvalue1 = map(EMGread1, 0, 1023, 0, 255);
  EMGvalue2 = map(EMGread2, 0, 1023, 0, 255);
  // Get the EMG difference to determine to which side the motor with go and how fast
  /*EMGctrl = EMGvalue1 - EMGvalue2;


  //smoothing
  
  total = total - EMGbuffer[buffIdx];   // subtract the last reading
  EMGbuffer[buffIdx] = EMGctrl;         // read from the sensor
  total = total + EMGbuffer[buffIdx];   // add the reading to the total
  buffIdx = buffIdx + 1;                // advance to the next position in the array
  // if we're at the end of the array wrap around to the beginning:
  if (buffIdx >= buffSize) {
    buffIdx = 0;
  }
  motorValue = total / buffSize;        // calculate the average and set the motor value

  // drive the motor
  
  if (motorValue > 10) //close
  {
    myMotor->setSpeed(abs(motorValue));
    myMotor->run(FORWARD);
    //myMotor->run(RELEASE);
  }
  if (motorValue < -10) //open, with a slight threshold for eliminating the noise
  {
    myMotor->setSpeed(abs(motorValue));
    myMotor->run(BACKWARD);
    //myMotor->run(RELEASE);*/
  }

  // print the results to the Serial Monitor:
  Serial.print(EMGvalue1);
  Serial.print('-');
  Serial.print(EMGvalue2);

  // wait 2 milliseconds before the next loop for the analog-to-digital
  // converter to settle after the last reading:
  delay(80);
  //myMotor->run(RELEASE);
}

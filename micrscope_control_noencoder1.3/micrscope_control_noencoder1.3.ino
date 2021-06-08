/*
Stepper motor control adn scan control for mictroscope
Joby Joseph. Adapted from 

 */

#include <Stepper.h>

const int stepsPerRevolution = 2048;  // change this to fit the number of steps per revolution

int my_x;
int my_tmp;
int myTOGLE=1;
char my_str[15];
String my_S;

int FirstLoc;   //First location
int LastLoc;    //Last location
int FirstLocSet=0;   //First location
int LastLocSet=0;    //Last location
int LocSet=0;  // Set to 1 if both LastLoc and FirstLoc are set
int SliceStep=50;  //Slice thickness in terms of steps (Default) Will  be set from the python
int MoveFLG=0;  //Moving if set. Used to exit from movez() function too. Will get set to zero by limit switches.


int StepperPosition=0;    // To store the current Stepper Motor Position based on rotary encoder. May be replaced with motor instruction count if the stepper is reliable
int StepsToTake=4;      // Controls the speed of the Stepper per Rotary click

// for your motor
int tmp=1;
// Wiring:
// Pin 8 to IN1 on the ULN2003 driver
// Pin 9 to IN2 on the ULN2003 driver
// Pin 10 to IN3 on the ULN2003 driver
// Pin 11 to IN4 on the ULN2003 driver
// Create stepper object called 'myStepper', note the pin order:
Stepper myStepper = Stepper(stepsPerRevolution, 8, 10, 9, 11);

void setup() 
  {
  pinMode(12, OUTPUT);  //LED  for testing
  pinMode(5, INPUT);  //UP switch 
  pinMode(6, INPUT);  //DOWN switch 
  
  // Set the speed to 15 rpm:
  myStepper.setSpeed(15);
  
  // Begin Serial communication at a baud rate of 9600:
  Serial.begin(115200);
  }

void loop() 
  {
  int TMPloc;
  if (Serial.available() > 0)
    {
    my_S = Serial.readString();
    my_x = my_S.toInt();  
    delay(10);
    //Serial.println(my_S);
    //sprintf(my_str,"Sprintf %d \n",my_x + 1);
    // Serial.println(my_str);
    
    digitalWrite(12, HIGH);
    switch(my_x)
      {
      case 1:    //Set current positions as fist location z
        FirstLoc=StepperPosition;
        FirstLocSet=1;
        if (LastLocSet==1)
          {
          LocSet=1;
          if (LastLoc>FirstLoc)
            {
            TMPloc=LastLoc;
            LastLoc=FirstLoc;
            FirstLoc=TMPloc;
            }
          }
        Serial.println(my_x);
        break;
      case 2:   //Set current position as last location z
        LastLoc=StepperPosition;
        LastLocSet=1;
        if (FirstLocSet==1)
          {
          LocSet=1; 
          if (LastLoc>FirstLoc)
            {
            TMPloc=LastLoc;
            LastLoc=FirstLoc;
            FirstLoc=TMPloc;
            }
          }
        Serial.println(my_x);
        break;
      case 3:   //Scan
        if (LocSet==1)   //Scan only if First and Last are set
          {
          LocSet=1;
          Serial.println(my_x);
          scanstack();
          }
        break;
      case 4:  //REad slice thickness
          Serial.println(my_x);
          while (Serial.available()<=0)
            delay(10);
          my_S = Serial.readString();
          SliceStep = my_S.toInt();
          delay(10);
          Serial.println(SliceStep);
          delay(10);
          break;
//        delay(100);
//        SliceStep=Serial.readString();
//        SliceStep = my_S.toInt(); 
          SliceStep = 100;   //100 steps per slice. Later to be got from python
      default:
        break;
      }
   

//    while(my_x>0)
//      {
//      my_x=my_x-1;
//      Serial.println(my_x);
//      delay(10);   
//      }
    digitalWrite(12, LOW);
    }
  if (digitalRead(5))
    {
  //  Serial.println(StepperPosition-StepsToTake);
    MoveFLG=1; 
    movez(StepperPosition-StepsToTake);
    }
           
  if (digitalRead(6))
    {
   // Serial.println(StepperPosition+StepsToTake);
    MoveFLG=1; 
    movez(StepperPosition+StepsToTake); 
    }
  }

  
void scanstack()   //To scan a stack
  {
  int LocalFLG=1;
  if (LocSet==1)  //Checking if First and last are set. Then step through the slices based on step size, waiting for completion of each slice. Using serial communication
    {
    MoveFLG=1;
    movez(FirstLoc);  //To start the scan
    //myStepper.step(FirstLoc-StepperPosition);  ////To start the scan
    delay(10);
    //StepperPosition= FirstLoc;
    Serial.println(10);
    delay(100);
    //Serial.flush();
    while (LocalFLG)
      {  
      if (Serial.available())
        {
        my_S = Serial.readString();
        my_x = my_S.toInt(); 
        Serial.println(my_x);  
        delay(10);
        if (my_x==12)
          {
          MoveFLG=1; 
          movez(StepperPosition-SliceStep);  //To start the scan
         // myStepper.step(-SliceStep);  ////To start the scan
        //  delay(500);
        //  StepperPosition= StepperPosition-SliceStep;
         // Serial.println(StepperPosition); 
          if (StepperPosition < LastLoc)
            {
            Serial.println(11);
        //    Serial.flush();
            delay(10); 
            LocalFLG=0;
            break;
            }
          else
            Serial.println(10);
            delay(10); 
          //  Serial.flush();
          }
        }
      }
//    Serial.println(12);  
//    Serial.println(11);
    }
  else             //Else only single slice. Wait for completion.
    {
    }
  LocSet=0;
  }


void movez(int TargetLoc)  //Move motor by steps while
  {
  int StepVal=3;
  while (MoveFLG==1)  
    {
    if (StepperPosition<TargetLoc)
      {
      myStepper.step(StepVal);
      StepperPosition=StepperPosition+StepVal;
      delay(10);
      }
    else if (StepperPosition>TargetLoc)
      {
      myStepper.step(-StepVal);
      StepperPosition=StepperPosition-StepVal;
      delay(10);
      }
    else   //Reached TargetLoc
      {
      MoveFLG=0;
      }
    if (abs(StepperPosition-TargetLoc)<(StepVal+1)) 
      {
      MoveFLG=0;  
      }
    }
  }

//
//// Interrupt routine runs if CLK goes from HIGH to LOW
//void rotarydetect ()  
//  {
//  cli(); //stop interrupts happening before we read pin values
//  delay(4);  // delay for Debouncing
//  if (digitalRead(PinCLK))
//    {
//    StepperPosition++;
//    rotationdirection= digitalRead(PinDT);
//    }
//  else
//    {
//    rotationdirection= !digitalRead(PinDT);
//    StepperPosition--;
//    }
//  sei(); //restart interrupts
//  }

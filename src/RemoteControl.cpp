#include <AutonomousCarSystem.h>

// Constructor
RemoteControl::RemoteControl()
{

}

void RemoteControl::begin(Driver* driverRef, Parking* parkingRef)
{
  driver  = driverRef;
  parking = parkingRef;
  timeoutCounter = millis();
  timeoutLock = false;
}

void RemoteControl::listen() {
  if (Serial3.available()) {
    char command = Serial3.read();
    switch (command) {
      case _PARKING:
        if (parking -> isParking())
            parking -> stop();
        else
            parking -> start(parking -> _PARALLEL);
        break;

      case _FORWARD: case _REVERSE: case _LEFT: case _RIGHT:
        if (parking -> isParking()) // overrides
          parking -> stop();
        manualControl(command);
      break;

      default:
        if (parking -> isParking())
          parking -> stop();
        else
          driver -> drive(0);
        break;
    }
  } else if (timeoutLock && millis() > (150 + timeoutCounter)) {
      driver -> drive(0);
      driver -> setAngle(0);
      timeoutLock = false;
    }
  }

void RemoteControl::manualControl(char command) {
  if(driver -> isAuto())
    driver -> setManualControl();
  switch (command) {
    case _FORWARD:
      driver -> drive(45);
      driver -> setAngle(0);
      break;

    case _REVERSE:
      driver -> drive(-45);
      driver -> setAngle(0);
      break;

    case _LEFT:
      driver -> drive(45);
      driver -> setAngle(-75);
      break;

    case _RIGHT:
      driver -> drive(45);
      driver -> setAngle(75);
      break;
  }
  timeoutLock = true;
  timeoutCounter = millis();
}

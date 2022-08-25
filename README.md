# Raspberry Pi with Camera

![](Resources/OVwCameraPI.png)


## What did you need?

Raspberry Pi with Camera

My Android App that you can download from Google Play here:
* [OV Grabber (with ADS)](https://play.google.com/store/apps/details?id=com.edodm85.ovgrabber.free)
* [OV Grabber PRO (without ADS)](https://play.google.com/store/apps/details?id=com.edodm85.ovgrabber.paid)

## How does it work?

Raspberry:

1. Clone the project:

 ```shell
$ git clone git@github.com:edodm85/Raspberry_Pi_and_Camera_Board.git

$ cd Raspberry_Pi_and_Camera_Board
  ```

2. Run the script

 ```shell
$ python3 CameraPI_SNAP_over_WIFI_DOT.py
  ```

<br>

OV Grabber:

1. Connect Phone and PC over the same WIFI network

2. Open the Application "OV Grabber" on phone

3. In the "TCP Settings" menu insert the Raspberry IP and PORT

4. In the "GRABBER Settings" menu insert the Image resolution and format

5. In the main page press CONNECT 

6. Then INIT and SNAP for acquire an image


<br>

The protocol description is here: https://github.com/edodm85/DOT_Protocol_Specification


<br>
  
  
  

## License

> Copyright (C) 2022 edodm85.  
> Licensed under the MIT license.  
> (See the [LICENSE](https://github.com/edodm85/Raspberry_Pi_and_Camera_Board/blob/master/LICENSE) file for the whole license text.)

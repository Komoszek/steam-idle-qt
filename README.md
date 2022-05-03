# steam-idle-qt
This utility aims to be easy to use reimplementation of [IdleMaster](https://github.com/jshackles/idle_master_py) for Linux using PyQt6. It is (probably) based on work of
[michael-n0813](https://github.com/michael-n0813/linux-idle-master/)

## Requirements
1. PyQt6
2. PyQt6-WebEngine
3. colorama
4. beautifulsoup4

## Running
To run this application you need to have running Steam app, then simply launch `steam-idle-qt` directory in this repository with python i.e.:
```
python steam-idle-qt/
```
After starting this app you will be greeted by Steam login page where you have to sign in with your Steam account.

To start auto-idling, check Auto-idle box. If you want to manually start/stop idlying, switch to `Games` tab and double click on one of the entries.

## Features
- Integrated Steam signing in
- Fast Mode - idlying in multiple games at the same time
- Auto-Idlying
- Integrated Open Steam button

## Credits
- [michael-n0813](https://github.com/michael-n0813) - [Python version of idle master](https://github.com/michael-n0813/linux-idle-master/) which this app is based on
- [jshackles](https://github.com/jshackles) - Original Idle Master and python version

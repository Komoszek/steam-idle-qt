#!/usr/bin/env python3

import bs4
import re
import sys
import os
import logging
import platform

from colorama import init, Fore
from PyQt6.QtNetwork import QNetworkRequest, QNetworkCookie, QNetworkAccessManager, QNetworkReply, QNetworkCookieJar
from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QTreeWidget, QCheckBox, QTreeWidgetItem
from PyQt6.QtCore import Qt, QTimer, QUrl, QProcess, QObject
from PyQt6.QtGui import QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView

from ctypes import CDLL

init()

secureCookie = QNetworkCookie(b"steamLoginSecure", b"")
steamUserID = ""
DelayTime = 10
steamStatus = None
steamSignedIn = None
lastLoggedStatus = None
steamtext = ""
autoIdle = False
fastMode = False
fastModeInit = False
cookieStore = None

os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))

logging.basicConfig(filename="steamqtidle.log",filemode="w",format="[ %(asctime)s ] %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p",level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.WARNING)
console.setFormatter(logging.Formatter("[ %(asctime)s ] %(message)s", "%m/%d/%Y %I:%M:%S %p"))
logging.getLogger('').addHandler(console)

logging.warning(Fore.GREEN + "WELCOME TO STEAM IDLE QT" + Fore.RESET)


def get_steam_api():
    if sys.platform.startswith('linux'):
        if platform.architecture()[0].startswith('32bit'):
            print('Loading Linux 32bit library')
            steam_api = CDLL('./libsteam_api32.so')
        elif platform.architecture()[0].startswith('64bit'):
            print('Loading Linux 64bit library')
            steam_api = CDLL('./libsteam_api64.so')
        else:
            print('Linux architecture not supported')
    else:
        print('Operating system not supported')
        return False

    return steam_api


steam_api = get_steam_api()

class IdleProcessManager(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.processes = {}
        self.gameTimer = {}
        self.fastModeTimer = None


    def idleStart(self, appID, refreshData=True):
        try:
            logging.warning("Starting game " + appID + " to idle cards")
            if appID not in self.processes.keys() and steamStatus and steamSignedIn:
                self.processes[appID] = [QProcess(), None]
                self.processes[appID][0].start('python3', ['./steam-idle-instance.py', appID])
                mainWin.startIdleText(appID)

                if refreshData:
                    BadgeManager.updateApp(appID)
                    imageManager.getImage(appID)
            else:
                if not steamStatus:
                    logging.warning(Fore.RED + "Steam is not running" + Fore.RESET)

                if not steamSignedIn:
                    logging.warning(Fore.RED + "You are not signed in" + Fore.RESET)

                if appID in self.processes.keys():
                    logging.warning(Fore.RED + "App is already running" + Fore.RESET)

        except:
            logging.warning(Fore.RED + "Error launching steam-idle-instance with game ID " + str(appID) + Fore.RESET)
            del self.processes[appID]
        

    def idleChill(self, appID):
        if appID in self.processes.keys():
            try:
                if not BadgeManager.List[appID][1] == "1":
                    timeout = 900000
                else:
                    timeout = 300000
                logging.warning(Fore.GREEN + "Chilling " + str(appID) + " for " + str(timeout/60000) + " minutes"+ Fore.RESET)

                self.processes[appID][1] = QTimer()
                self.processes[appID][1].setSingleShot(True)
                self.processes[appID][1].setInterval(timeout)
                self.processes[appID][1].timeout.connect(lambda: (BadgeManager.updateApp(appID)))
                self.processes[appID][1].start()

            except Exception as e:
                logging.warning(Fore.RED + e + Fore.RED)
                pass

    def idleFastModeGameUpdate(self, appID, i):
        self.idleStart(appID, False)
        self.processes[appID][1] = QTimer()
        self.processes[appID][1].setSingleShot(True)
        self.processes[appID][1].setInterval(10000)
        self.processes[appID][1].timeout.connect(lambda: (self.idleClose(appID)))
        self.processes[appID][1].start()

    def idleFastModeUpdate(self):
        games = list(BadgeManager.List.keys())
        self.closeAllIdles()

        for i in range(len(games)):
            self.gameTimer[games[i]] = QTimer()
            self.gameTimer[games[i]].setSingleShot(True)

            self.gameTimer[games[i]].setInterval(11000*i+1000)
            self.gameTimer[games[i]].timeout.connect(lambda appID=games[i],x=i: (self.idleFastModeGameUpdate(appID,x)))
            self.gameTimer[games[i]].start()

        self.fastModeTimer = QTimer()
        self.fastModeTimer.setSingleShot(True)
        self.fastModeTimer.setInterval(11000*len(games)+1000)
        self.fastModeTimer.timeout.connect(self.idleFastModeInit)
        self.fastModeTimer.start()

    def idleFastModeInit(self):
        if len(BadgeManager.List) != 0:
            global fastModeInit
            fastModeInit = True
            BadgeManager.update()
            timeout = 1800000

            games = list(BadgeManager.List.keys())

            for appID in games:
                idleManager.idleStart(appID,False)

            self.fastModeTimer = QTimer()
            self.fastModeTimer.setSingleShot(True)
            # 30 minutes
            self.fastModeTimer.setInterval(timeout)

            logging.warning(Fore.GREEN + "Fast mode idle of " + str(', '.join(games)) + " for " + str(timeout/60000) + " minutes"+ Fore.RESET)

            self.fastModeTimer.timeout.connect(lambda: (self.idleFastModeUpdate()))
            self.fastModeTimer.start()

    def idleClose(self, appID):
        if appID not in self.processes.keys():
            return

        mainWin.stopIdleText(appID)
        logging.warning(Fore.GREEN + "Stopped Idle of " + str(appID) + Fore.RESET)

        try:
            self.gameTimer[appID].stop()
        except:
            pass
        try:
            self.processes[appID][0].kill()
        except:
            pass
        try:
            self.processes[appID][1].stop()
        except:
            pass
        try:
            del self.processes[appID]
        except:
            pass
        BadgeManager.updateApp(appID)
        mainWin.label.setPixmap(QPixmap())

    def closeAllIdles(self):
        gamesToClose = list( idleManager.processes.keys())

        for appID in gamesToClose:
            try:
                self.idleClose(appID)
            except:
                pass

    def closeFinishedIdles(self):
        for appID in self.processes.keys():
            if appID not in BadgeManager.List.keys():
                self.idleClose(appID)

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        global steam_api

        self.setMinimumSize(460, 70)
        self.setMaximumSize(460, 70)

        self.setWindowTitle("Steam Idle Qt")

        centralWidget = QWidget(self)
        self.setCentralWidget(centralWidget)

        mainLayout = QGridLayout()
        centralWidget.setLayout(mainLayout)
        mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        statusLayout = QVBoxLayout()
        statusLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.steamStatusTitle = QLabel("Checking Steam status", self)
        statusLayout.addWidget(self.steamStatusTitle)
        statusLayout.setAlignment(self.steamStatusTitle, Qt.AlignmentFlag.AlignTop)
        self.steamStatusTitle.setOpenExternalLinks(True)

        self.loggedInTitle = QLabel("Signing in...", self)

        self.loggedInTitle.linkActivated.connect(self.linkClicked)

        self.loggedInWidget = QHBoxLayout()
        self.loggedInWidget.addWidget(self.loggedInTitle)


        statusLayout.addLayout(self.loggedInWidget)
        statusLayout.setAlignment(self.loggedInWidget, Qt.AlignmentFlag.AlignTop)

        self.tabWidget = QTabWidget()
        self.currentIdleTabWidget = QWidget()
        self.currentIdleTabLayout = QVBoxLayout()

        self.currentIdleTabWidget.setLayout(self.currentIdleTabLayout)
        self.label = QLabel()
        self.label.setScaledContents(True)
        self.currentIdleTabLayout.addWidget(self.label)


        self.badgeListWidget = QTreeWidget()
        self.badgeListWidget.setColumnCount(4)
        self.badgeListWidget.hideColumn(0)
        self.badgeListWidget.setHeaderLabels(["appID","Game title", "Remaining cards", "Idle state"])
        self.badgeListWidget.itemDoubleClicked.connect(self.dbclicked)

        mainLayout.addLayout(statusLayout,0,0,1,1)

        navigationLayout = QHBoxLayout()

        self.autoIdleCheckbox = QCheckBox("Auto-idle")
        self.autoIdleCheckbox.stateChanged.connect(self.autoIdleChange)

        navigationLayout.addWidget(self.autoIdleCheckbox)

        self.fastModeCheckbox = QCheckBox("Fast Mode")
        self.fastModeCheckbox.stateChanged.connect(self.fastModeChange)
        navigationLayout.addWidget(self.fastModeCheckbox)

        mainLayout.addLayout(navigationLayout,0,1,1,1)
        self.tabWidget.addTab(self.currentIdleTabWidget, "Currently idling")
        self.tabWidget.addTab(self.badgeListWidget,"Games")
        self.tabWidget.setVisible(False)
        mainLayout.addWidget(self.tabWidget,1,0,1,2)

    def StatusUpdate(self):
        global steamStatus, lastLoggedStatus, steamtext, autoIdle, fastModeInit
        newSteamStatus = steam_api.SteamAPI_IsSteamRunning()

        if steamStatus != newSteamStatus:
            steamStatus = newSteamStatus
            if steamStatus:
                self.steamStatusTitle.setText("Steam is running")
            else:
                idleManager.closeAllIdles()
                self.steamStatusTitle.setText("Steam is not running <a href=\"steam:\/\/run\">Open it</a>")

        if steamSignedIn:
            if not lastLoggedStatus == steamSignedIn:
                pass
            mainWin.loggedInTitle.setText("Signed in <a href=\"signout\">(Sign out)</a>")
        elif steamSignedIn == False:
            idleManager.closeAllIdles()
            mainWin.loggedInTitle.setText("Not signed in <a href=\"signin\">(Sign in)</a>")

        if steamStatus and steamSignedIn and autoIdle and len(idleManager.processes) == 0 and len(BadgeManager.List):
            if fastMode == False:
                firstgame = list(BadgeManager.List.keys())[0]
                idleManager.idleStart(firstgame)
            elif fastModeInit == False:
                idleManager.idleFastModeInit()

        lastLoggedStatus = steamSignedIn

    def expand(self):
        self.setMinimumSize(460, 310)
        self.setMaximumSize(460, 310)
        self.tabWidget.setVisible(True)

    def collapse(self):
        self.setMinimumSize(460, 70)
        self.setMaximumSize(460, 70)
        self.tabWidget.setVisible(False)

    def resetFastMode(self):
        global fastModeInit
        fastModeInit = False
        try:
            idleManager.fastModeTimer.stop()
        except:
            pass

        for timer in idleManager.gameTimer:
            try:
                timer.stop()
            except:
                pass

    def autoIdleChange(self, state):
        global autoIdle

        self.resetFastMode()

        if state == 2:
            autoIdle = True
        elif state == 0:
            autoIdle = False

    def fastModeChange(self, state):
        global fastMode

        self.resetFastMode()

        if state == 2:
            fastMode = True
        elif state == 0:
            fastMode = False
        
        try:
            idleManager.closeAllIdles()
        except:
            pass

    def linkClicked(self, url):
        global web
        if url == "signout":
            global cookieStore, secureCookie, steamSignedIn, steamUserID
            cookieStore.deleteAllCookies()
            steamSignedIn = False
            steamUserID = ""
            secureCookie = QNetworkCookie(b"steamLoginSecure", b"")
            cookieStore = None

            BadgeManager.setCookieJar(QNetworkCookieJar())
            self.badgeListWidget.clear()
            idleManager.closeAllIdles()
            BadgeManager.List.clear()
            self.collapse()
        else:
            web = SteamBrowser(self, True)
            web.show()

    def closeEvent(self, event):
        idleManager.closeAllIdles()
        sys.exit()

    def dbclicked(self, item):
        appID = item.text(0)
        if appID in idleManager.processes.keys():
            idleManager.idleClose(appID)
        else:
            idleManager.idleStart(appID)

    def addListItem(self, item):
        newItem = QTreeWidgetItem()
        newItem.setText(0, item[0])
        newItem.setText(1, item[1])
        newItem.setText(2, item[2])
        self.badgeListWidget.addTopLevelItem(newItem)
        return newItem

    def updateIdleText(self, appID):
        BadgeManager.GetItem(appID).setText(3, "Idling" if appID in self.processes.keys() else "" )

    def startIdleText(self, appID):
        try:
            (BadgeManager.getItem(appID)).setText(3, "Idling")
        except:
            pass

    def stopIdleText(self, appID):
        try:
            BadgeManager.getItem(appID).setText(3, "")
        except:
            pass


    def removeListItem(self, item):
        try:
            self.badgeListWidget.takeTopLevelItem(self.badgeListWidget.indexOfTopLevelItem(item))
        except Exception as e:
            logging.warning(Fore.RED + e + Fore.RESET)

class BadgeManager(QNetworkAccessManager):
    def __init__(self):
        QNetworkAccessManager.__init__(self)
        self.finished.connect(self.requestFinished)
        self.List = {}

    def getItem(self, appID):
        try:
            return self.List[appID][2]
        except Exception as e:
            logging.warning(Fore.RED + e + Fore.RESET)

    def updateCookie(self, cookie):
        tempCookieJar = QNetworkCookieJar()
        tempCookieJar.insertCookie(cookie)
        self.setCookieJar(tempCookieJar)

    def update(self, pageNum=1):
        if steamSignedIn:
            url = "https://steamcommunity.com/id/" + steamUserID + "/badges?l=english&p=" + str(pageNum)
            req = QNetworkRequest(QUrl(url))
            self.get(req)
        else:
            logging.warning(Fore.RED + "Not signed in" + Fore.RESET)

    def updateApp(self, appID):
        if steamSignedIn:
            url = "https://steamcommunity.com/id/" + steamUserID + "/gamecards/" + str(appID) + "?l=english"
            req = QNetworkRequest(QUrl(url))
            self.get(req)
        else:
            logging.warning(Fore.RED + "Not signed in" + Fore.RESET)

    def requestFinished(self, reply):
        global fastModeInit
        er = reply.error()
        if er == QNetworkReply.NetworkError.NoError:
            badgePageData = bs4.BeautifulSoup(reply.readAll().data().decode('utf8'))

            userinfo = badgePageData.find("a",{"class":"user_avatar"})
            if not userinfo:
                global steamSignedIn
                mainWin.collapse()
                steamSignedIn = False
                return

            badgeSet = badgePageData.find_all("div",{"class":"badge_title_row"})

            for badge in badgeSet:
                try:
                    dropCount = badge.find_all("span",{"class": "progress_info_bold"})[0].contents[0]
                    href = badge.find_all("a",{"class":"how_to_get_card_drops"})[0]["href"]
                    gameData = re.findall(r"ShowCardDropInfo\( \"(.*)\",.*_gamebadge_(\d*)", href)

                    if "No card drops" in dropCount: # or (has_playtime == False and authData["hasPlayTime"].lower() == "true") :
                        try:
                            mainWin.removeListItem(self.List[gameData[0][1]][2])
                        except:
                            pass
                        try:
                            del self.List[gameData[0][1]]
                        except:
                            pass
                        try:
                            idleManager.idleClose(gameData[0][1])
                        except:
                            pass
                    else:
                        dropCountInt = re.search("^(\d+)", dropCount).group(1)

                        if gameData[0][1] in self.List:
                            self.List[gameData[0][1]][1] = dropCountInt
                            self.List[gameData[0][1]][2].setText(2, dropCountInt)
                        else:
                            self.List[gameData[0][1]] = [gameData[0][0], dropCountInt, None]

                            self.List[gameData[0][1]][2] = mainWin.addListItem([gameData[0][1], gameData[0][0], dropCountInt])

                        #it will call timout if game is idling
                        if fastMode == False:
                            idleManager.idleChill(gameData[0][1])


                except Exception as e:
                    continue

            if str(reply.url())[-1] == "1":
                try:
                    badgePages = int(badgePageData.find_all("a",{"class": "pagelink"})[-1].text)
                    currentPage = 2
                    while currentPage <= badgePages:
                        self.update(currentPage)
                        currentPage += 1
                except:
                    pass

            if fastModeInit and len(BadgeManager.List) == 0:
                idleManager.resetFastMode()
            idleManager.closeFinishedIdles()
        else:
            logging.warning(Fore.RED + "Error occured: " + er + Fore.RESET)
            logging.warning(Fore.RED + reply.errorString() + Fore.RESET)


class SteamBrowser(QWebEngineView):
    def __init__(self, parent, cookieClear=False):
        super(SteamBrowser, self).__init__(parent)
        global cookieStore, steam_api

        if cookieClear:
            mainWin.collapse()

        if cookieStore == None:
            cookieStore = self.page().profile().cookieStore()
            cookieStore.cookieAdded.connect(self.cookieAdd)
            cookieStore.cookieRemoved.connect(self.cookieRemove)

        self.setMinimumSize(640, 480)
        self.setWindowTitle("Sign in into Steam")
        self.setWindowFlags(Qt.WindowType.Dialog)

        self.load(QUrl("https://steamcommunity.com/login"))

        self.urlChanged.connect(self.urlChangeFun)

        self.loadFinished.connect(self.run)

    def run(self):
        self.page().runJavaScript("window.scrollTo(0,0)")
        self.page().runJavaScript("(function (){try{return RegExp('id\/(.*)\/\"','g').exec(document.getElementsByClassName('playerAvatar')[0].innerHTML)[1]}catch(e){return ''}})();",self.ready)

    def ready(self, val):
        global steamUserID, steamSignedIn, secureCookie
        steamUserID = val
        if val == "":
            steamSignedIn = False
            self.show()
        else:
            mainWin.expand()
            steamSignedIn = True

            BadgeManager.update()
            self.deleteLater()
            self.close()

    def urlChangeFun(self, url):
        global secureCookie, steamSignedIn, steamUserID
        if secureCookie.value() != b"":
            id = re.findall('/\w+$', url.path())[0]
            self.ready(id)
        else:
            self.setUrl(QUrl("https://steamcommunity.com/login"))


    def cookieAdd(self, cookie):
        global secureCookie, steamSignedIn, BadgeManager
        if cookie.name() == b"steamLoginSecure" and not cookie.value() == secureCookie.value():
            BadgeManager.updateCookie(cookie)
            secureCookie = cookie


    def cookieRemove(self, cookie):
        global secureCookie, steamSignedIn
        if cookie.name() == b"steamLoginSecure":
            secureCookie = cookie
            steamSignedIn = False


class ImageManager(QNetworkAccessManager):
    def __init__(self):
        QNetworkAccessManager.__init__(self)
        self.finished.connect(self.response)

    def getImage(self, appID):
        url = "https://steamcdn-a.akamaihd.net/steam/apps/" + str(appID) + "/header.jpg"
        req = QNetworkRequest(QUrl(url))
        self.get(req)

    def response(self, reply):
        er = reply.error()
        if er == QNetworkReply.NetworkError.NoError:
            newimage = QPixmap()
            newimage.loadFromData(reply.readAll())
            mainWin.label.setPixmap(newimage.scaled(mainWin.label.size(), Qt.AspectRatioMode.KeepAspectRatio,  Qt.TransformationMode.SmoothTransformation) )
        else:
            logging.warning(Fore.RED + "Error occured: " + er + Fore.RESET)
            logging.warning(Fore.RED + reply.errorString() + Fore.RESET)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Steam Idle Qt")
    BadgeManager = BadgeManager()
    imageManager = ImageManager()
    idleManager = IdleProcessManager()
    mainWin = MainWindow()
    mainWin.show()

    timer = QTimer()
    timer.timeout.connect(mainWin.StatusUpdate)
    timer.start(1000)

    mainWin.StatusUpdate()
    web = SteamBrowser(mainWin)

    sys.exit(app.exec())

import bs4
import time
import re
import sys
import os
import logging
import datetime
import platform
from colorama import init, Fore, Back, Style
from PyQt5 import QtCore, QtWidgets, QtNetwork
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import * #QMainWindow, QLabel, QGridLayout, QWidget
from PyQt5.QtCore import QSize, QThread, pyqtSignal, QTimer, QUrl, pyqtSlot, QProcess, QObject
from PyQt5.QtGui import QPixmap
from PyQt5.QtWebEngineWidgets import *

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

os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))

logging.basicConfig(filename="idlemaster.log",filemode="w",format="[ %(asctime)s ] %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p",level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.WARNING)
console.setFormatter(logging.Formatter("[ %(asctime)s ] %(message)s", "%m/%d/%Y %I:%M:%S %p"))
logging.getLogger('').addHandler(console)

logging.warning(Fore.GREEN + "WELCOME TO IDLE MASTER" + Fore.RESET)


def get_steam_api():
    if sys.platform.startswith('win32'):
        print('Loading Windows library')
        steam_api = CDLL('steam_api.dll')
    elif sys.platform.startswith('linux'):
        if platform.architecture()[0].startswith('32bit'):
            print('Loading Linux 32bit library')
            steam_api = CDLL('./libsteam_api32.so')
        elif platform.architecture()[0].startswith('64bit'):
            print('Loading Linux 64bit library')
            steam_api = CDLL('./libsteam_api64.so')
        else:
            print('Linux architecture not supported')
    elif sys.platform.startswith('darwin'):
        print('Loading OSX library')
        steam_api = CDLL('./libsteam_api.dylib')
    else:
        print('Operating system not supported')
        return False

    return steam_api


steam_api = get_steam_api()


class IdleProcessManager(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.processes = {}

    def idleStart(self, appID):
        if len(self.processes) == 0:
            try:
                # logging.warning("Starting game " + getAppName(appID) + " to idle cards")

                # idle_time = time.time()

                if appID not in self.processes.keys() and steamStatus and steamSignedIn:
                    self.processes[appID] = [QProcess(), None]
                    self.processes[appID][0].start("python steam-idle-instance.py " + str(appID))
                    mainWin.startIdleText(appID)
                    BadgeManager.updateApp(appID)
                    imageManager.getImage(appID)
                else:
                    if not steamStatus:
                        print("Steam is not running")

                    if not steamSignedIn:
                        print("You are not signed in")

                    if appID in self.processes.keys():
                        print("App is already running")

            except:
                logging.warning(Fore.RED + "Error launching steam-idle-instance with game ID " + str(appID) + Fore.RESET)
                del self.processes[appID]

    def idleChill(self, appID):
        if appID in self.processes.keys():
            try:
                print(appID)
                if not BadgeManager.List[appID][1] == "1":
                    timeout = 900000
                else:
                    timeout = 300000

                print("Chilling for " + str(timeout/60000) + " minutes")
                self.processes[appID][1] = QTimer()
                self.processes[appID][1].setSingleShot(True)
                self.processes[appID][1].setInterval(timeout)
                self.processes[appID][1].timeout.connect(lambda: (BadgeManager.updateApp(appID)))
                self.processes[appID][1].start()

            except Exception as e:
                print(e)
                pass

    def idleClose(self, appID):
        try:
            mainWin.stopIdleText(appID)
            print("Stopped Idle of " + str(appID))
            self.processes[appID][0].kill()
            self.processes[appID][1].stop()
            del self.processes[appID]
            mainWin.label.setPixmap(QPixmap())
        except Exception as e:
            print(e)
            pass

    def closeAllIdles(self):
        try:
            for appID in idleManager.processes.keys():
                idleManager.idleClose(appID)
        except:
            pass

    def closeFinishedIdles(self):
        for appID in self.processes.keys():
            if appID in BadgeManager.List.keys():
                self.idleClose(appID)



def StatusUpdate():
    global steamStatus, lastLoggedStatus, steamtext, autoIdle

    steamStatus = steam_api.SteamAPI_IsSteamRunning()
    if steamStatus:
        #steamtext += "a"
        #mainWin.steamStatusTitle.setText(steamtext)
        mainWin.steamStatusTitle.setText("Steam is running")
    else:
        idleManager.closeAllIdles()
        mainWin.steamStatusTitle.setText("Steam is not running <a href=\"steam:\/\/run\">Open it</a>")

    if steamSignedIn:
        if not lastLoggedStatus == steamSignedIn:
            pass
        mainWin.loggedInTitle.setText("Signed in <a href=\"signout\">(Sign out)</a>")
    elif steamSignedIn == False:
        idleManager.closeAllIdles()
        mainWin.loggedInTitle.setText("Not signed in <a href=\"signin\">(Sign in)</a>")

    if steamStatus and steamSignedIn and autoIdle and len(idleManager.processes) == 0 and len(BadgeManager.List):
        firstgame = list(BadgeManager.List.keys())[0]
        idleManager.idleStart(firstgame)



    """if steamStatus and steamSignedIn and len(BadgeManager.List) and len(idleManager.processes) == 0:
        firstgame = list(BadgeManager.List.keys())[0]
        idleManager.idleStart(firstgame)"""

    lastLoggedStatus = steamSignedIn

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        steam_api = get_steam_api()

        self.setMinimumSize(460, 70)
        self.setMaximumSize(460, 70)

        self.setWindowTitle("Steam Idle Qt")

        centralWidget = QWidget(self)
        self.setCentralWidget(centralWidget)

        mainLayout = QGridLayout(self)
        centralWidget.setLayout(mainLayout)
        mainLayout.setAlignment(QtCore.Qt.AlignTop)
        statusLayout = QVBoxLayout(self)
        statusLayout.setAlignment(QtCore.Qt.AlignTop)

        self.steamStatusTitle = QLabel("Checking Steam status", self)
        statusLayout.addWidget(self.steamStatusTitle)
        statusLayout.setAlignment(self.steamStatusTitle, QtCore.Qt.AlignTop)
        self.steamStatusTitle.setOpenExternalLinks(True)

        self.loggedInTitle = QLabel("Signing in...", self)

        self.loggedInTitle.linkActivated.connect(self.linkClicked)
        """self.loggedInClick.setStyleSheet("QLabel { color : blue;}");
        self.loggedInClick.setCursor(QtCore.Qt.ArrowCursor);

        self.loggedInClick"""

        self.loggedInWidget = QHBoxLayout()
        self.loggedInWidget.addWidget(self.loggedInTitle)


        statusLayout.addLayout(self.loggedInWidget)
        statusLayout.setAlignment(self.loggedInWidget, QtCore.Qt.AlignTop)

        """
        newwidget = QWidget()
        newwidget.setLayout(statusLayout)
        """

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

        navigationLayout = QHBoxLayout(self)
        self.autoIdleCheckbox = QCheckBox("Auto-idle")

        self.autoIdleCheckbox.stateChanged.connect(self.autoIdleChange)


        navigationLayout.addWidget(self.autoIdleCheckbox)

        mainLayout.addLayout(navigationLayout,0,1,1,1)
        self.tabWidget.addTab(self.currentIdleTabWidget, "Currently idling")
        self.tabWidget.addTab(self.badgeListWidget,"Games")
        self.tabWidget.setVisible(False)
        mainLayout.addWidget(self.tabWidget,1,0,1,2)


        #mainLayout.addWidget(self.badgeListWidget)
    def expand(self):
        self.setMinimumSize(460, 310)
        self.setMaximumSize(460, 310)
        self.tabWidget.setVisible(True)

    def collapse(self):
        self.setMinimumSize(460, 70)
        self.setMaximumSize(460, 70)
        self.tabWidget.setVisible(False)

    def autoIdleChange(self, state):
        global autoIdle
        if state == 2:
            autoIdle = True
        elif state == 0:
            autoIdle = False

    def linkClicked(self, url):
        global web
        if url == "signout":
            web = SteamBrowser(mainWin, True)
        else:
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

        #print(item.text(0), item.text(1))

    def addListItem(self, item):
        newItem = QTreeWidgetItem()
        newItem.setText(0, item[0])
        newItem.setText(1, item[1])
        newItem.setText(2, item[2])
        self.badgeListWidget.addTopLevelItem(newItem)
        return newItem

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
            print(e)

class BadgeManager(QtNetwork.QNetworkAccessManager):
    def __init__(self):
        QtNetwork.QNetworkAccessManager.__init__(self)
        self.finished.connect(self.requestFinished)
        self.List = {}

    def getItem(self, appID):
        try:
            return self.List[appID][2]
        except Exception as e:
            print(e)

    def updateCookie(self, cookie):
        tempCookieJar = QNetworkCookieJar()
        tempCookieJar.insertCookie(cookie)
        self.setCookieJar(tempCookieJar)

    def update(self, pageNum=1):
        if steamSignedIn:
            url = "https://steamcommunity.com/id/" + steamUserID + "/badges?l=english&p=" + str(pageNum)
            req = QtNetwork.QNetworkRequest(QUrl(url))
            self.get(req)
        else:
            print("Not signed in")

    def updateApp(self, appID):

        if steamSignedIn:
            url = "https://steamcommunity.com/id/" + steamUserID + "/gamecards/" + str(appID) + "?l=english"
            req = QtNetwork.QNetworkRequest(QUrl(url))
            self.get(req)
        else:
            print("Not signed in")

    def requestFinished(self, reply):
        er = reply.error()
        if er == QtNetwork.QNetworkReply.NoError:
            badgePageData = bs4.BeautifulSoup(reply.readAll().data().decode('utf8'))

            userinfo = badgePageData.find("a",{"class": "user_avatar"})
            if not userinfo:
                global steamSignedIn
                mainWin.collapse()
                steamSignedIn = False
                return

            badgeSet = badgePageData.find_all("div",{"class":"badge_title_row"})

            if str(reply.url())[-20:] == "badges?l=english&p=1":
                self.List.clear()
                idleManager.closeAllIdles(self)


            for badge in badgeSet:
                try:
                    dropCount = badge.find_all("span",{"class": "progress_info_bold"})[0].contents[0]
                    href = badge.find_all("a",{"class":"how_to_get_card_drops"})[0]["href"]
                    gameData = re.findall(r"ShowCardDropInfo\( \"(.*)\",.*_gamebadge_(\d*)", href)
                    #has_playtime = re.search("[0-9\.] hrs on record", badge_text) != None
                    if "No card drops" in dropCount: # or (has_playtime == False and authData["hasPlayTime"].lower() == "true") :
                        try:
                            del self.List[gameData[0][1]]
                            idleManager.idleClose(gameData[0][1])
                        except:
                            pass
                        continue
                    else:
                        dropCountInt = re.search("^(\d+)", dropCount).group(1)


                        if gameData[0][1] in self.List:
                            self.List[gameData[0][1]][1] = dropCountInt
                        else:
                            self.List[gameData[0][1]] = [gameData[0][0], dropCountInt, None]

                            self.List[gameData[0][1]][2] = mainWin.addListItem([gameData[0][1], gameData[0][0], dropCountInt])

                        #it will call timout if game is idling
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
        else:
            print("Error occured: ", er)
            print(reply.errorString())




class SteamBrowser(QWebEngineView):
    def __init__(self, parent, cookieClear=False):
        super(SteamBrowser, self).__init__(parent)
        steam_api = get_steam_api()

        if cookieClear:
            global steamSignedIn
            self.page().profile().cookieStore().deleteAllCookies()
            BadgeManager.setCookieJar(QNetworkCookieJar())
            mainWin.badgeListWidget.clear()
            idleManager.closeAllIdles()
            BadgeManager.List.clear()
            mainWin.collapse()
            steamSignedIn = False

        self.setMinimumSize(640, 480)
        self.setWindowTitle("Sign in into Steam")

        self.setWindowFlags(QtCore.Qt.Dialog)

        self.load(QUrl("https://steamcommunity.com/login"))
        self.page().profile().cookieStore().cookieAdded.connect(self.cookieAdd)
        self.page().profile().cookieStore().cookieRemoved.connect(self.cookieRemove)

        #self.urlChanged.connect(self.urlChangeFun)

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

    def urlChangeFun(self):
        if steamSignedIn and not steamUserID == "":
            self.deleteLater()
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
        QtNetwork.QNetworkAccessManager.__init__(self)
        self.finished.connect(self.response)

    def getImage(self, appID):
        url = "https://steamcdn-a.akamaihd.net/steam/apps/" + str(appID) + "/header.jpg"
        #url = "http://cdn.akamai.steamstatic.com/steam/apps/" + str(appID) + "/header_292x136.jpg"
        req = QtNetwork.QNetworkRequest(QUrl(url))
        self.get(req)

    def response(self, reply):
        er = reply.error()
        if er == QtNetwork.QNetworkReply.NoError:
            newimage = QPixmap()
            newimage.loadFromData(reply.readAll())
            mainWin.label.setPixmap(newimage.scaled(  mainWin.label.size(), QtCore.Qt.KeepAspectRatio,  QtCore.Qt.SmoothTransformation) )

        else:
            print("Error occured: ", er)
            print(reply.errorString())

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    BadgeManager = BadgeManager()
    imageManager = ImageManager()

    timer = QTimer()
    timer.timeout.connect(StatusUpdate)
    timer.start(1000)

    idleManager = IdleProcessManager()

    mainWin = MainWindow()
    mainWin.show()
    StatusUpdate()
    web = SteamBrowser(mainWin)

    sys.exit(app.exec_())

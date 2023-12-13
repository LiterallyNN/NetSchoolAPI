from requests import Session
import hashlib # md5


class NS_LoginType:
    """
        LoginType[LoginType["ServAdmin"] = 0] = "ServAdmin";
        LoginType[LoginType["School"] = 1] = "School";
        LoginType[LoginType["EducManager"] = 2] = "EducManager";
        LoginType[LoginType["EducManagerForSchool"] = 3] = "EducManagerForSchool";
        LoginType[LoginType["Idp"] = 8] = "Idp";
        LoginType[LoginType["Refresh"] = 9] = "Refresh";
    """

    ServAdmin = 0
    School = 1
    EducManager = 2
    EducManagerForSchool = 3
    Idp = 8
    Refresh = 9

class NetSchoolAPI:
    def __init__(self, school: str, login: str, password: str, url: str = "https://giseo.rkomi.ru"):
        """
            school должно содержать либо точное название, либо название, при котором первая школа из предложенных - нужная
        """
        self.url = url

        self.login = login
        self.password = password
        self.school = school
        
        self.__login_data = {}
        self.__school = {}
        self.__data = {}
        self.__school = {}

        self.session = Session()
        self.session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Origin": self.url,
            "Sec-Ch-Ua-Platform": "Windows",
            "Sec-Ch-Ua": '"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"'
        })

        self.__get_school()
        self.__get_data()
        self.__login()

    def announcements(self, take: int = -1):
        request = self.session.get(f"{self.url}/webapi/announcements", params={
            "take": take # -1 = последние посты
        }, headers={
            "Referer": f"{self.url}/angular/school/announcements/"
        })

        if request.status_code != 200:
            print(request.text)
            raise Exception(f"[NetSchoolAPI | announcements]: status_code != 200 ({request.status_code})")
        
        return request.json()

    def get_attachment(self, id: str):
        request = self.session.get(f"{self.url}/webapi/attachments/{id}")
        
        if request.status_code != 200:
            raise Exception(f"[NetSchoolAPI | get_attachment]: status_code != 200 ({request.status_code})")

        return {
            "success": True,
            "content": request.content
        }

    def logout(self):
        """
            var vers = null;
            if (parameters.nocache && typeof window.getVer == "function") {
                vers = (_a = window.getVer()) === null || _a === void 0 ? void 0 : _a.toString();
                createHiddenField(form, 'VER', vers);
            }
            VER можно игнорировать
        """
        if self.__data == {} or self.__login_data == {} or not self.__login_data.get("at"):
            return
        
        request = self.session.post(f"{self.url}/webapi/auth/logout", params={
            "at": self.__login_data["at"]
        })

        if request.status_code != 200: # иногда может 302 отправлять, это нормально
            raise Exception(f"[NetSchoolAPI | logout]: status_code != 200 ({request.status_code})")
        print("Logout")
        self.__login_data = {}

    def __get_school(self):
        request = self.session.get(f"{self.url}/webapi/schools/search", params={
            "withAddress": "true",
            "name": self.school
        })

        if len(request.json()) < 1:
            raise Exception(f"[NetSchoolAPI | __get_school]: can't find school {self.school}")
        
        self.__school = request.json()[0]
        print(f"School short name: {self.__school["shortName"]}, id: {self.__school["id"]}")

    def __get_data(self):
        request = self.session.post(f"{self.url}/webapi/auth/getdata")

        if request.status_code != 200:
            raise Exception("[NetSchoolAPI | __get_data]: status_code != 200") 

        self.__data = request.json()
        print(f"Data:\n\tlt: {self.__data['lt']}\n\tver: {self.__data['ver']}\n\tsalt: {self.__data['salt']}")
    
    def __login(self):
        """
            var pw2 = hexMD5_(authData.salt + hexMD5_(password));
            var authParams = Object.assign({}, {
                lt: authData.lt,
                pw2: pw2,
                ver: authData.ver,
                un: loginName
            }, addOpts);
            if (schoolId > 0) {
                authParams.scid = schoolId;
                authParams.loginType = _login.LoginType.School;
            } else if (emId > 0) {
                authParams.emid = emId;
                authParams.loginType = _login.LoginType.EducManager;
            }
        """
        request = self.session.post(f"{self.url}/webapi/auth/login", params={
            "loginType": NS_LoginType.School, # Поменять если надо другое
            "lt": self.__data["lt"],
            "ver": self.__data["ver"],
            "un": self.login,
            "pw2": hashlib.md5((self.__data["salt"] + hashlib.md5(self.password.encode("utf-8")).hexdigest()).encode("utf-8")).hexdigest(),
            "scid": self.__school["id"]
        }, headers={ # без хедеров не пускает
            "Referer": f"{self.url}/authorize/login"
        })

        if request.status_code != 200:
            print(request.text)
            print(request.headers)
            print(self.session.cookies)
            raise Exception("[NetSchoolAPI | __login]: status_code != 200")
        
        self.__login_data = request.json()
        self.session.headers.update({
            "At": self.__login_data["at"]
        })
        print(f"Logged-in as {self.__login_data["accountInfo"]["user"]["name"]}")

from bs4 import BeautifulSoup
import json
import re
import requests
from collections import Counter
import mysql.connector
import re

semester = 32234


dicts = {'subjectsName': [],
         'lecturersName': [],
         'subjectsTime': {

}
}





subjectPage = requests.get(
    "http://etimetable.unisel.edu.my/BJ{}/BJ{}_subjects_days_vertical.html".format(semester, semester))
teachersPage = requests.get(
    "http://etimetable.unisel.edu.my/BJ{}/BJ{}_teachers_days_vertical.html".format(semester, semester))


subjectSoup = BeautifulSoup(subjectPage.content, 'html.parser')
teachersSoup = BeautifulSoup(teachersPage.content, 'html.parser')

subjects = subjectSoup.find_all('li')
lecturers = teachersSoup.find_all('li')
availSub = subjectSoup.select("table > tbody > tr")

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="timetable"

)

print(mydb)
mycursor = mydb.cursor()
mycursor.execute("TRUNCATE TABLE subjects")
mycursor.execute("TRUNCATE TABLE lecturers")
mycursor.execute("TRUNCATE TABLE subjectsTime")


# For lecturers table
############################
for lecturer in lecturers:

    lecturer = lecturer.text.strip('\n').strip()

    dicts['lecturersName'].append(lecturer)


for lecturer in dicts['lecturersName']:

    lecturer = re.split('-|\n', lecturer)

    if (len(lecturer) != 2):

        lecturerDept = lecturer[0]
        lecturer.pop(0)
        lecturer = [lecturerDept, ' '.join(lecturer)]

    else:
        lecturer = lecturer

    sql = "INSERT INTO lecturers (lectDept, lectName) VALUES (%s, %s)"
    val = (lecturer[0], lecturer[1])
    mycursor.execute(sql, val)

    mydb.commit()


# For subjects table
############################
for subject in subjects:

    subject = subject.text.strip('\n').replace('Subject', '').strip()

    dicts['subjectsName'].append(subject)


for subject in dicts['subjectsName']:

    if len(re.split('-|\n', subject)) == 1:
        subject = re.split('-|\n', subject)

        
       
    else:
        subject = re.split('-|\n', subject)
    
   
 
        
    if (len(subject) != 2):

        subjectCode = subject[0]
        subject.pop(0)
        subject = [subjectCode.strip(), ' '.join(subject)]
    else:
        subject = subject
        
    

    subjectCode = subject[0]
    subjectName = subject[1]

    
    
    m = re.search(r'\d+$', subjectCode)
    if m is None:
        
    
        res = re.findall(r'(\w+?)(\d+)', subjectCode)
        
        
        temp = res[0][0] + res[0][1]
        
        tempSplit = subjectCode.split(temp)
        
        subjectName = tempSplit[1] + subjectName
        
        subjectCode = temp
    
    
    
    
    if (subjectName.startswith('/')):
        tempSubName = subjectName[:8]
        subjectCode = subjectCode + tempSubName
        subjectCode = subjectCode.replace(" ", '')
        subjectName = subjectName.replace(tempSubName, '')
        subjectName = subjectName.lstrip(' ')
    elif (subjectName.startswith(' / ')):
        tempSubName = subjectName[:10]
        subjectCode = subjectCode + tempSubName
        subjectCode = subjectCode.replace(" ", '')
        subjectName = subjectName.replace(tempSubName, '')
        subjectName = subjectName.lstrip(' ')
        
    
    subjectCode = subjectCode.replace(" ", '') 
    subjectName = subjectName.lstrip(' ')
    
    # Check if the subject code is accidentally combined with the subject name
    m = re.search(r'\d+$', subjectCode)
    # if the string ends in digits m will be a Match object, or None otherwise.
    if m is not None:
        if subjectCode[-2].isalpha():
            unformatted = subjectCode
            subjectCode = subjectCode[0:7]
            unformatted = unformatted.replace(subjectCode, '')
            subjectName = unformatted
     
            
        
    


    subjectSql = "INSERT IGNORE INTO subjects (subjectCode, subjectName) VALUES (%s, %s)"
    valSubjects = (subjectCode, subjectName)
    mycursor.execute(subjectSql, valSubjects)

    subjectSql = "INSERT IGNORE INTO subjectsTime (subjectCode) VALUES ('{}')".format(
        subjectCode)

    mycursor.execute(subjectSql)

    mydb.commit()


# Delete duplicate subjects wherever possible
duplicateSqlSub = "DELETE n1 FROM subjects n1, subjects n2 WHERE n1.id > n2.id AND n1.subjectCode = n2.subjectCode"
duplicateSqlTime = "DELETE n1 FROM subjectsTime n1, subjectsTime n2 WHERE n1.id > n2.id AND n1.subjectCode = n2.subjectCode"
mycursor.execute(duplicateSqlSub)
mycursor.execute(duplicateSqlTime)

mydb.commit()


# For subjectsTime table
############################

for idx, time in enumerate(availSub):

    time = time.text.strip('\n').strip()

    time = re.split('\n', time)

    time.pop(0)


    if (len(time) != 1):

        dict = {'time': time}

        dicts['subjectsTime'][idx] = dict


mycursor.execute("SELECT MAX(id) from subjects;")

myresult = mycursor.fetchone()



for x in range(myresult[0] * 6):

    

    if (x % 6 + 1 == 1):
        day = 'Monday'
    elif (x % 6 + 1 == 2):
        day = 'Tuesday'
    elif (x % 6 + 1 == 3):
        day = 'Wednesday'
    elif (x % 6 + 1 == 4):
        day = 'Thursday'
    elif (x % 6 + 1 == 5):
        day = 'Friday'

    day = day.lower()

    l_replace = [s.replace("'", "") for s in dicts['subjectsTime'][x]['time']]

    if(l_replace == []):
        continue

    sql = 'UPDATE subjectsTime SET {} = "{}" WHERE id = {}'.format(
        day, l_replace, x // 6 + 1)

    mycursor.execute(sql)

    mydb.commit()


with open("sample.json", "w") as outfile:
    json.dump(dicts['subjectsTime'], outfile)

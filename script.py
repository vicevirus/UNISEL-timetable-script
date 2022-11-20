from bs4 import BeautifulSoup
import json
import sys


import re
import requests
from collections import Counter
import mysql.connector
import re



if sys.argv[1] == "--semester":
    if sys.argv[2].isnumeric():
        semester = int(sys.argv[2])

else:
    print("Please enter a semester or correct input")
    sys.exit(1)

    
if sys.argv[3] == "--campus":
    if sys.argv[4] == "BJ" or "SA":
        campus = sys.argv[4]
else:
    print("Please enter a campus or correct input")
    sys.exit(1)

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="timetable"

)


mycursor = mydb.cursor()
mycursor.execute("TRUNCATE TABLE {}subjects".format(campus))
mycursor.execute("TRUNCATE TABLE {}lecturers".format(campus))
mycursor.execute("TRUNCATE TABLE {}subjectsTime".format(campus))




dicts = {'subjectsName': [],
         'lecturersName': [],
         'subjectsTime': {

}
}


subjectPage = requests.get(
    "http://etimetable.unisel.edu.my/{}{}/{}{}_subjects_days_vertical.html".format(campus, semester, campus, semester))
teachersPage = requests.get(
    "http://etimetable.unisel.edu.my/{}{}/{}{}_teachers_days_vertical.html".format(campus, semester, campus, semester))


subjectSoup = BeautifulSoup(subjectPage.content, 'html.parser')
teachersSoup = BeautifulSoup(teachersPage.content, 'html.parser')

subjects = subjectSoup.find_all('li')
lecturers = teachersSoup.find_all('li')
availSub = subjectSoup.select("table > tbody > tr")



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

    sql = "INSERT INTO {}lecturers (lectDept, lectName) VALUES (%s, %s)".format(campus)
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

    subjectRef = subject[0]

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

    if (len(subjectCode) < 7):
        subjectCode = subjectRef.replace(" ", '')

    subjectSql = "INSERT IGNORE INTO {}subjects (subjectCode, subjectName) VALUES (%s, %s)".format(campus)
    valSubjects = (subjectCode, subjectName)
    mycursor.execute(subjectSql, valSubjects)

    subjectSql = "INSERT IGNORE INTO {}subjectsTime (subjectCode) VALUES ('{}')".format(campus, subjectCode)

    mycursor.execute(subjectSql)

    mydb.commit()


# # Delete duplicate subjects wherever possible
# duplicateSqlSub = "DELETE n1 FROM subjects n1, subjects n2 WHERE n1.id > n2.id AND n1.subjectCode = n2.subjectCode"
# duplicateSqlTime = "DELETE n1 FROM subjectsTime n1, subjectsTime n2 WHERE n1.id > n2.id AND n1.subjectCode = n2.subjectCode"
# mycursor.execute(duplicateSqlSub)
# mycursor.execute(duplicateSqlTime)

# mydb.commit()


# For subjectsTime table
############################

for idx, time in enumerate(availSub):

    time = time.text.strip('\n').strip()

    time = re.split('\n', time)

    time.pop(0)

    if (len(time) != 1):

        dict = {'time': time}

        dicts['subjectsTime'][idx] = dict


mycursor.execute("SELECT MAX(id) from {}subjects;".format(campus))

myresult = mycursor.fetchone()

counter = 0

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

    tableTime = [s.replace("'", "") for s in dicts['subjectsTime'][x]['time']]

    if(tableTime == []):
        continue
    blankTime = ['---', '---', '---', '---', '---',
                 '---', '---', '---', '---', '---', '---']

    if (tableTime == blankTime):

        continue

    sql = 'UPDATE {}subjectsTime SET {} = "{}" WHERE id = {}'.format(
        campus, day, tableTime, x // 6 + 1)

    mycursor.execute(sql)

    mydb.commit()

sql = "SELECT id FROM {}subjectsTime WHERE (monday IS NULL) AND (tuesday IS NULL) AND (wednesday IS NULL) AND (thursday IS NULL) AND (friday IS NULL)".format(campus)


mycursor.execute(sql)

result = mycursor.fetchall()

for x in range(len(result)):
    subjectDupSql = "DELETE FROM {}subjects WHERE id = {}".format(campus, result[x][0])
    timeDupSql = "DELETE FROM {}subjectsTime WHERE id = {}".format(campus, result[x][0])
    mycursor.execute(subjectDupSql)
    mycursor.execute(timeDupSql)

    mydb.commit()




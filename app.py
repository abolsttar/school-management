from abc import ABC, abstractmethod
import db
import json

users = {'admin': 'admin'}
current_user = None

def login(username, password):
    global current_user
    if users.get(username) == password:
        current_user = username
        return True
    return False

def load_all():
    try:
        db.init_db()
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

def save_all():
    try:
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False
class Person(ABC):
    def __init__(self, id, name, family, phone, age, gender):
        self.id = id
        self.name = name
        self.family = family
        self.phone = phone
        self.age = age
        self.gender = gender
    @abstractmethod
    def info(self):
        pass
    def __str__(self):
        return self.info()

class Student(Person):
    def __init__(self, id, name, family, phone, student_code, gender, age, field):
        super().__init__(id, name, family, phone, age, gender)
        self.student_code = student_code
        self.field = field
    def info(self):
        return f"دانشجو: {self.name} {self.family} ({self.field})"
    def get_sections(self):
        enrollments = db.get_student_grades(self.id)
        return [Section.from_db(db.get_section_by_id(sec_id)) for sec_id, _ in enrollments]
    def get_grades(self):
        return {sec_id: grade for sec_id, grade in db.get_student_grades(self.id)}
    def average(self):
        grades = [grade for _, grade in db.get_student_grades(self.id) if grade is not None]
        return sum(grades) / len(grades) if grades else 0.0
    
    @staticmethod
    def from_db(row):
        if not row:
            return None
        return Student(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])

class Teacher(Person):
    def __init__(self, id, name, family, phone, gender, age, edu, history):
        super().__init__(id, name, family, phone, age, gender)
        self.edu = edu
        self.history = history
    def info(self):
        return f"استاد: {self.name} {self.family} ({self.edu})"
    def get_sections(self):
        return [Section.from_db(row) for row in db.get_sections() if row[2] == self.id]
    
    @staticmethod
    def from_db(row):
        if not row:
            return None
        return Teacher(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])

class Course:
    def __init__(self, id, code, title, vahed, dars_type, prerequisites):
        self.id = id
        self.code = code
        self.title = title
        self.vahed = vahed
        self.dars_type = dars_type
        self.prerequisites = prerequisites.split(',') if prerequisites else []
    def __str__(self):
        return f"{self.code} - {self.title} ({self.vahed} واحد, {self.dars_type})"
    def get_sections(self):
        return [Section.from_db(row) for row in db.get_sections() if row[1] == self.id]

class ClassRoom:
    def __init__(self, id, name, capacity):
        self.id = id
        self.name = name
        self.capacity = capacity
    def __str__(self):
        return f"کلاس {self.name} (ظرفیت: {self.capacity})"
    def get_sections(self):
        return [Section.from_db(row) for row in db.get_sections() if row[3] == self.id]

class Section:
    def __init__(self, id, course_id, teacher_id, class_room_id, time):
        self.id = id
        self.course_id = course_id
        self.teacher_id = teacher_id
        self.class_room_id = class_room_id
        self.time = time
    @staticmethod
    def from_db(row):
        if not row:
            return None
        return Section(row[0], row[1], row[2], row[3], row[4])
    def get_students(self):
        return [Student.from_db(db.get_student_by_id(sid)) for sid, _ in db.get_section_students(self.id)]
    def get_grades(self):
        return {sid: grade for sid, grade in db.get_section_students(self.id)}
    def __str__(self):
        course = db.get_course_by_id(self.course_id)
        teacher = db.get_teacher_by_id(self.teacher_id)
        class_room = db.get_class_room_by_id(self.class_room_id)
        return f"سکشن {course[2]} ({self.time}) - استاد: {teacher[1]} - کلاس: {class_room[1]}"
    @staticmethod
    def get_all():
        return [Section.from_db(row) for row in db.get_sections()]

class University:
    def __init__(self, name="دانشگاه تهران", place="تهران"):
        self.name = name
        self.place = place

university = University()
def get_all_students():
    return [Student.from_db(row) for row in db.get_students()]
def get_all_teachers():
    return [Teacher.from_db(row) for row in db.get_teachers()]
def get_all_courses():
    return [Course(row[0], row[1], row[2], row[3], row[4], row[5]) for row in db.get_courses()]
def get_all_class_rooms():
    return [ClassRoom(row[0], row[1], row[2]) for row in db.get_class_rooms()]
def get_all_classrooms():
    return get_all_class_rooms()
def get_all_sections():
    return [Section.from_db(row) for row in db.get_sections()]
add_student = db.add_student
get_students = db.get_students
get_student_by_code = db.get_student_by_code
update_student = db.update_student
delete_student = db.delete_student
remove_student = db.delete_student
add_teacher = db.add_teacher
get_teachers = db.get_teachers
get_teacher_by_id = db.get_teacher_by_id
update_teacher = db.update_teacher
delete_teacher = db.delete_teacher
remove_teacher = db.delete_teacher
add_dars = db.add_course
get_dars_list = db.get_courses
get_dars_by_code = db.get_course_by_code
update_dars = db.update_course
delete_dars = db.delete_course
add_class_room = db.add_class_room
get_class_rooms = db.get_class_rooms
get_class_room_by_name = db.get_class_room_by_name
update_class_room = db.update_class_room
delete_class_room = db.delete_class_room
add_section = db.add_section
get_sections = db.get_sections
get_section_by_id = db.get_section_by_id
update_section = db.update_section
delete_section = db.delete_section
enroll_student = db.enroll_student
set_grade = db.set_grade
get_enrollments = db.get_enrollments
get_student_grades = db.get_student_grades
get_section_students = db.get_section_students 
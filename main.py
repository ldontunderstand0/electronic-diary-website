import smtplib
import flask as fl
import flask_sqlalchemy as fls
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = fl.Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dbase.db'
app.config.update(SECRET_KEY=os.urandom(24))
db = fls.SQLAlchemy(app)
login_manager = LoginManager(app)

smtpObj = smtplib.SMTP('smtp.mail.ru', 587)
smtpObj.starttls()
smtpObj.login('','')


class UserLogin():

    def __init__(self):
        self.__user = None

    def create(self, user):
        self.__user = user
        return self

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self .__user.id)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer)
    email = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_teacher = db.Column(db.Integer)
    is_admin = db.Column(db.Integer)

    def __repr__(self):
        return '<User %r>' % self.id

    def get_id(self):
        return str(self.id)

    def is_authenticated(self):
        return True


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    shortname = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return '<Group %r>' % self.id


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    name = db.Column(db.String(100), nullable=False)
    shortname = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return '<Subject %r>' % self.id


class SubjectGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer)
    subject_id = db.Column(db.Integer)

    def __repr__(self):
        return '<SubjectGroup %r>' % self.id


class Lession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_group_id = db.Column(db.Integer)
    kind = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return '<Lession %r>' % self.id


class LessionUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    presence = db.Column(db.Integer)
    grade = db.Column(db.Integer)
    lession_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)

    def __repr__(self):
        return '<LessionUser %r>' % self.id


@login_manager.user_loader
def load_user(user_id):
    print("load_user", user_id)
    return User.query.get(user_id)


@app.route('/logout')
def logout():
    if current_user.get_id() is None:
        return fl.redirect('/')
    logout_user()
    fl.flash("Вы вышли из аккаунта", "success")
    return fl.redirect('/')


@app.route('/', methods=['POST', 'GET'])
def index():
    if current_user.get_id() is not None:
        user = User.query.get(current_user.get_id())
        if user.is_admin:
            return fl.redirect('/admin')
        if user.is_teacher:
            return fl.redirect('/subject')
        else:
            return fl.redirect('/stats/' + user.login)
    if fl.request.method == 'POST':
        login = fl.request.form['floatingInput']
        password = fl.request.form['floatingPassword']
        user = User.query.filter_by(login=login, password=password).first()
        print(user.id)
        if user is not None:
            userlogin = UserLogin().create(user)
            login_user(userlogin)
            return fl.redirect('/')
        fl.flash('Неверный логин или пароль', 'error')
        return fl.render_template('index.html')
    else:
        return fl.render_template('index.html')


@app.route('/subject')
def subject():
    if current_user.get_id() is None:
        return fl.redirect('/')
    user = User.query.get(current_user.get_id())
    if not user.is_teacher:
        return fl.redirect('/')
    if user.is_admin:
        subject = Subject.query.all()
    else:
        subject = Subject.query.filter_by(user_id=user.id)
    dict = {
            'type':'subject',
            'title': 'Предметы',
            'name':'Ваши предметы',
            'btn_name':'Выбрать предмет',
            'shortname': '',
            'user_name': User.query.get(current_user.get_id()).name
            }
    return fl.render_template('list.html', list=subject, dict=dict)


@app.route('/subject/<string:shortname>')
def subject_group(shortname):
    if current_user.get_id() is None:
        return fl.redirect('/')
    user = User.query.get(current_user.get_id())
    if not (user.is_teacher or user.is_admin):
        return fl.redirect('/')
    dict = {
            'type': 'group',
            'title': 'Группы',
            'name': 'Группы',
            'btn_name': 'Выбрать группу',
            'shortname': shortname,
            'user_name': User.query.get(current_user.get_id()).name
            }
    subject_id = Subject.query.filter_by(shortname=shortname).first().id
    groups = SubjectGroup.query.filter_by(subject_id=subject_id)
    group_list = []
    for group in groups:
        print(group.group_id)
        group_list.append(Group.query.get(group.group_id))
    return fl.render_template('list.html', list=group_list, dict=dict)


@app.route('/subject/<string:subject_name>/<string:group_name>', methods=['POST', 'GET'])
def table(subject_name, group_name):
    if current_user.get_id() is None:
        return fl.redirect('/')
    user = User.query.get(current_user.get_id())
    if not (user.is_teacher or user.is_admin):
        return fl.redirect('/')
    group_id = Group.query.filter_by(shortname=group_name).first().id
    subject_id = Subject.query.filter_by(shortname=subject_name).first().id
    subject_group_id = SubjectGroup.query.filter_by(group_id=group_id, subject_id=subject_id).first().id

    if fl.request.method == 'POST':
        try:
            lession_id, user_id = map(int, fl.request.form['id'].split('_'))
            lession_user = LessionUser.query.filter_by(lession_id=lession_id, user_id=user_id).first()

            lession = Lession.query.get(lession_id)
            if lession.kind == 'Лекция':
                lession_user.grade = 0
            else:
                lession_user.grade = int(fl.request.form['listGroup'])
            lession_user.presence = int(fl.request.form['listG'])

            db.session.commit()
        except KeyError:

            kind = fl.request.form['listGroupRadios']
            date = fl.request.form['date']

            lession = Lession(subject_group_id=subject_group_id, kind=kind, date=date)
            db.session.add(lession)
            db.session.commit()
        return fl.redirect('/subject/' + subject_name + '/' + group_name)

    else:
        lessions = Lession.query.filter_by(subject_group_id=subject_group_id)
        users = User.query.filter_by(group_id=group_id)

        grades = []
        for user in users:
            sum = 0
            count = 0
            rate = 0
            rcount = 0
            grade = []
            for lession in lessions:
                lession_user = LessionUser.query.filter_by(lession_id=lession.id, user_id=user.id).first()
                rcount += 1
                if lession_user is None:
                    presence = 0
                    g = 0
                    lession_id = lession.id
                    user_id = user.id

                    lession_user = LessionUser(presence=presence, grade=g, lession_id=lession_id, user_id=user_id)
                    db.session.add(lession_user)
                    db.session.commit()
                dc = {
                    'id': lession_user.id,
                    'grade': '',
                    'lession_id': lession_user.lession_id,
                    'user_id': lession_user.user_id,
                    'is_grade': 1
                }
                if lession_user.presence:
                    rate += 1
                if lession.kind == 'Лекция':
                    dc['is_grade'] = 0
                    if lession_user.presence:
                        dc['grade'] = '+'
                    else:
                        dc['grade'] = '-'
                else:
                    sum += lession_user.grade
                    count += 1
                    dc['grade'] = lession_user.grade
                grade.append(dc)

            if count == 0:
                count += 1
            if rcount == 0:
                rcount += 1
            d = {
                'name': user.name,
                'perc': int((rate / rcount) * 100),
                'avg': format(sum / count, '.2f'),
                'grade': grade
            }
            grades.append(d)

        dict = {
            'subject_name': subject_name,
            'user_name': User.query.get(current_user.get_id()).name,
            'group_name': group_name
        }
        return fl.render_template('table.html', dict=dict, grades=grades, lessions=lessions, group_name=group_name)


@app.route('/admin')
def admin():
    if current_user.get_id() is None:
        return fl.redirect('/')
    if not User.query.get(current_user.get_id()).is_admin:
        return fl.redirect('/')
    list = ['user', 'group', 'subject', 'subject_group', 'lession', 'lession_user']
    dict = {
        'type': 'admin',
        'title': 'Админ',
        'name': 'Таблицы БД',
        'btn_name': 'Выбрать таблицу',
        'shortname': '',
        'user_name': User.query.get(current_user.get_id()).name
    }

    return fl.render_template('list.html', list=list, dict=dict)


@app.route('/admin/<string:str>')
def admin_table(str):
    if current_user.get_id() is None:
        return fl.redirect('/')
    if not User.query.get(current_user.get_id()).is_admin:
        return fl.redirect('/')
    form = []
    list = []
    dict = {
        'user_name': User.query.get(current_user.get_id()).name
    }
    match str:
        case 'user':
            list = User.query.all()
            for i in range(len(list)):
                list[i] = [list[i].id, list[i].email, list[i].group_id, list[i].login, list[i].password, list[i].name,
                           list[i].is_teacher, list[i].is_admin]
            form = ['id', 'email', 'group_id', 'login', 'password', 'name', 'is_teacher', 'is_admin']

        case 'group':
            list = Group.query.all()
            for i in range(len(list)):
                list[i] = [list[i].id, list[i].name, list[i].shortname]
            form = ['id', 'name', 'shortname']

        case 'subject':
            list = Subject.query.all()
            for i in range(len(list)):
                list[i] = [list[i].id, list[i].user_id, list[i].name, list[i].shortname]
            form = ['id', 'user_id', 'name', 'shortname']

        case 'subject_group':
            list = SubjectGroup.query.all()
            for i in range(len(list)):
                list[i] = [list[i].id, list[i].group_id, list[i].subject_id]
            form = ['id', 'group_id', 'subject_id']

        case 'lession':
            list = Lession.query.all()
            for i in range(len(list)):
                list[i] = [list[i].id, list[i].subject_group_id, list[i].kind, list[i].date]
            form = ['id', 'subject_group_id', 'kind', 'date']

        case 'lession_user':
            list = LessionUser.query.all()
            for i in range(len(list)):
                list[i] = [list[i].id, list[i].presence, list[i].grade, list[i].lession_id, list[i].user_id]
            form = ['id', 'presence', 'grade', 'lession_id', 'user_id']

    return fl.render_template('admin_table.html', list=list, form=form, name=str, dict=dict)


@app.route('/admin/<string:str>/update/<int:id>', methods=['POST', 'GET'])
def update(str, id):
    if current_user.get_id() is None:
        return fl.redirect('/')
    if not User.query.get(current_user.get_id()).is_admin:
        return fl.redirect('/')
    if fl.request.method == 'POST':
        match str:
            case 'user':
                user = User.query.get(id)

                user.group_id = fl.request.form['group_id']
                user.email = fl.request.form['email']
                user.login = fl.request.form['login']
                user.password = fl.request.form['password']
                user.name = fl.request.form['name']
                user.is_teacher = fl.request.form['is_teacher']
                user.is_admin = fl.request.form['is_admin']

                db.session.commit()

            case 'group':
                group = Group.query.get(id)
                group.name = fl.request.form['name']
                group.shortname = fl.request.form['shortname']

                db.session.commit()

            case 'subject':
                subject = Subject.query.get(id)
                subject.user_id = fl.request.form['user_id']
                subject.name = fl.request.form['name']
                subject.shortname = fl.request.form['shortname']

                db.session.commit()

            case 'subject_group':
                subject_group = SubjectGroup.query.get(id)
                subject_group.group_id = fl.request.form['group_id']
                subject_group.subject_id = fl.request.form['subject_id']

                db.session.commit()

            case 'lession':
                lession = Lession.query.get(id)

                lession.subject_group_id = fl.request.form['subject_group_id']
                lession.kind = fl.request.form['kind']
                lession.date = fl.request.form['date']

                db.session.commit()

            case 'lession_user':
                lession_user = LessionUser.query.get(id)
                lession_user.presence = fl.request.form['presence']
                lession_user.grade = fl.request.form['grade']
                lession_user.lession_id = fl.request.form['lession_id']
                lession_user.user_id = fl.request.form['user_id']

                db.session.commit()

        return fl.redirect('/admin/' + str)
    else:
        form = []
        match str:
            case 'user':
                user = User.query.get(id)
                form = [('group_id', user.group_id), ('email', user.email), ('login', user.login),
                        ('password',  user.password), ('name', user.name), ('is_teacher', user.is_teacher),
                        ('is_admin', user.is_admin)]

            case 'group':
                group = Group.query.get(id)
                form = [('name', group.name), ('shortname', group.shortname)]

            case 'subject':
                subject = Subject.query.get(id)
                form = [('user_id', subject.user_id), ('name', subject.name), ('shortname',subject.shortname)]

            case 'subject_group':
                subject_group = SubjectGroup.query.get(id)
                form = [('group_id', subject_group.group_id), ('subject_id', subject_group.subject_id)]

            case 'lession':
                lession = Lession.query.get(id)
                form = [('subject_group_id', lession.subject_group_id), (lession.kind, 'kind'), (lession.date, 'date')]

            case 'lession_user':
                lession_user = LessionUser.query.get(id)
                form = [('presence', lession_user.presence), ('grade', lession_user.grade),
                        ('lession_id',lession_user.lession_id), ('user_id', lession_user.user_id)]
        return fl.render_template('update.html', form=form)


@app.route('/admin/<string:str>/delete/<int:id>', methods=['POST', 'GET'])
def delete(str, id):
    if current_user.get_id() is None:
        return fl.redirect('/')
    if not User.query.get(current_user.get_id()).is_admin:
        return fl.redirect('/')
    obj = None
    match str:
        case 'user':
            obj = User.query.get(id)

        case 'group':
            obj = Group.query.get(id)

        case 'subject':
            obj = Subject.query.get(id)

        case 'subject_group':
            obj = SubjectGroup.query.get(id)

        case 'lession':
            obj = Lession.query.get(id)

        case 'lession_user':
            obj = LessionUser.query.get(id)

    db.session.delete(obj)
    db.session.commit()

    return fl.redirect('/admin/' + str)


@app.route('/admin/<string:str>/create', methods=['POST', 'GET'])
def create(str):
    if current_user.get_id() is None:
        return fl.redirect('/')
    if not User.query.get(current_user.get_id()).is_admin:
        return fl.redirect('/')
    if fl.request.method == 'POST':
        match str:
            case 'user':
                group_id = fl.request.form['group_id']
                email = fl.request.form['email']
                login = fl.request.form['login']
                password = fl.request.form['password']
                name = fl.request.form['name']
                is_teacher = fl.request.form['is_teacher']
                is_admin = fl.request.form['is_admin']

                user = User(group_id=group_id, email=email, name=name, is_teacher=is_teacher,
                            is_admin=is_admin, password=password, login=login)
                db.session.add(user)
                db.session.commit()

            case 'group':
                name = fl.request.form['name']
                shortname = fl.request.form['shortname']

                group = Group(name=name, shortname=shortname)
                db.session.add(group)
                db.session.commit()

            case 'subject':
                user_id = fl.request.form['user_id']
                name = fl.request.form['name']
                shortname = fl.request.form['shortname']

                subject = Subject(user_id=user_id, name=name, shortname=shortname)
                db.session.add(subject)
                db.session.commit()

            case 'subject_group':
                group_id = fl.request.form['group_id']
                subject_id = fl.request.form['subject_id']

                subject_group = SubjectGroup(group_id=group_id, subject_id=subject_id)
                db.session.add(subject_group)
                db.session.commit()

            case 'lession':
                subject_group_id = fl.request.form['subject_group_id']
                kind = fl.request.form['kind']
                date = fl.request.form['date']

                lession = Lession(subject_group_id=subject_group_id, kind=kind, date=date)
                db.session.add(lession)
                db.session.commit()

            case 'lession_user':
                presence = fl.request.form['presence']
                grade = fl.request.form['grade']
                lession_id = fl.request.form['lession_id']
                user_id = fl.request.form['user_id']

                lession_user = LessionUser(presence=presence, grade=grade, lession_id=lession_id, user_id=user_id)
                db.session.add(lession_user)
                db.session.commit()

        return fl.redirect('/admin/' + str)
    else:
        form = []
        match str:
            case 'user':
                form = ['group_id', 'email', 'login', 'password', 'name', 'is_teacher', 'is_admin']

            case 'group':
                form = ['name', 'shortname']

            case 'subject':
                form = ['user_id', 'name', 'shortname']

            case 'subject_group':
                form = ['group_id', 'subject_id']

            case 'lession':
                form = ['subject_group_id', 'kind', 'date']

            case 'lession_user':
                form = ['presence', 'grade', 'lession_id', 'user_id']

        return fl.render_template('create.html', form=form)


@app.route('/register', methods=['POST', 'GET'])
def reg():
    if current_user.get_id() is not None:
        user = User.query.get(current_user.get_id())
        if user.is_admin:
            return fl.redirect('/admin')
        if user.is_teacher:
            return fl.redirect('/subject')
        else:
            return fl.redirect('/stats/' + user.login)
    if fl.request.method == 'POST':

        group_id = Group.query.filter_by(name=fl.request.form['Группа']).first().id
        email = fl.request.form['Email']
        login = fl.request.form['Логин']
        password = fl.request.form['Пароль']
        name = fl.request.form['Имя']
        is_teacher = 0
        is_admin = 0

        user = User(group_id=group_id, email=email, name=name, is_teacher=is_teacher,
                    is_admin=is_admin, password=password, login=login)
        db.session.add(user)
        db.session.commit()

        return fl.redirect('/')
    else:

        form = ['Имя', 'Группа', 'Email', 'Логин', 'Пароль']

        return fl.render_template('register.html', form=form)


@app.route('/stats/<string:login>')
def stats(login):
    if current_user.get_id() is None:
        return fl.redirect('/')
    user = User.query.get(current_user.get_id())
    group = Group.query.get(user.group_id)
    subjects_group = SubjectGroup.query.filter_by(group_id=group.id)
    results = []
    for i in subjects_group:
        lessions = Lession.query.filter_by(subject_group_id=i.id)
        sum = 0
        count = 0
        rate = 0
        rcount = 0
        for j in lessions:
            rcount += 1
            lession_user = LessionUser.query.filter_by(lession_id=j.id, user_id=user.id).first()
            if lession_user is None:
                continue
            rate += 1
            if j.kind != 'Лекция':
                sum += lession_user.grade
                count += 1
        if not count:
            count += 1
        if not rcount:
            rcount += 1
        avg = format(sum / count, '.2F')
        perc = (rate / rcount) * 100

        results.append((Subject.query.get(i.id).name, avg, perc))

    dict = {
        'user_name': user.name,
    }
    return fl.render_template('stats.html', dict=dict, results=results)


@app.route('/subject/<string:subject_name>/<string:group_name>/info')
def info(subject_name, group_name):
    if current_user.get_id() is None:
        return fl.redirect('/')
    user_id = current_user.get_id()
    user_email = User.query.get(user_id).email
    group = Group.query.filter_by(shortname=group_name).first()
    users = User.query.filter_by(group_id=group.id)

    list = []
    for i in users:
        list.append([i.name, i.login, i.password])

    text = ''
    for line in list:
        text += 'ФИО:' + line[0] + ' login:' + line[1] + ' password:' + line[2] + '\n'

    msg = MIMEMultipart()

    msg["From"] = "kuznecov_stas12@mail.ru"
    msg["To"] = user_email
    msg["Subject"] = "Список аккаунтов студентов группы " + group.name

    msg.attach(MIMEText(text, "plain"))

    smtpObj.sendmail("kuznecov_stas12@mail.ru", user_email, msg.as_string())

    return fl.redirect(f'/subject/{subject_name}/{group_name}')


@app.route('/admin/<string:str>/info/<int:user_id>')
def info_admin(str, user_id):
    if current_user.get_id() is None:
        return fl.redirect('/')

    user = User.query.get(user_id)

    list = [[user.name, user.login, user.password]]

    text = ''
    for line in list:
        text += 'ФИО:' + line[0] + '\nlogin:' + line[1] + '\npassword:' + line[2] + '\n'

    msg = MIMEMultipart()

    msg["From"] = "kuznecov_stas12@mail.ru"
    msg["To"] = user.email
    msg["Subject"] = "Данные вашего аккаунта"

    msg.attach(MIMEText(text, "plain"))

    smtpObj.sendmail("kuznecov_stas12@mail.ru", user.email, msg.as_string())

    return fl.redirect(f'/admin/{str}')


if __name__ == '__main__':
    app.run(debug=True)
    smtpObj.quit()

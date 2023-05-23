import asyncio
from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template,
    url_for,
    flash,
    redirect,
    request,
)
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    current_user,
    logout_user,
    login_required,
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask import Flask, render_template, request, redirect, url_for, session
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    SelectField,
)
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-here"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(128))
    user_question_sets = db.relationship(
        "QuestionSet", back_populates="user", lazy=True
    )

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


class QuestionSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60), nullable=False)
    private = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="user_question_sets", lazy=True)

    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    label = db.Column(db.String(50), nullable=True)
    question_1 = db.Column(db.String(100), nullable=True)
    question_2 = db.Column(db.String(100), nullable=True)
    question_3 = db.Column(db.String(100), nullable=True)
    question_4 = db.Column(db.String(100), nullable=True)
    question_5 = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"QuestionSet('{self.title}', '{self.date_created}')"


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class RegistrationForm(FlaskForm):
    name = StringField("Username", validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Sign Up")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError(
                "That username is taken. Please choose a different one."
            )

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("That email is taken. Please choose a different one.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


class QuestionSetForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(min=5, max=100)])
    private = BooleanField("Private")
    label = StringField("Label", validators=[Length(max=50)])
    question_1 = TextAreaField("Question 1", validators=[Length(max=100)])
    question_2 = TextAreaField("Question 2", validators=[Length(max=100)])
    question_3 = TextAreaField("Question 3", validators=[Length(max=100)])
    question_4 = TextAreaField("Question 4", validators=[Length(max=100)])
    question_5 = TextAreaField("Question 5", validators=[Length(max=100)])
    submit = SubmitField("Create")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def home():
    public_sets = QuestionSet.query.filter_by(private=False).all()
    return render_template("home.html", public_sets=public_sets)


@app.route("/about")
def about():
    if current_user.is_authenticated:
        user_question_sets = QuestionSet.query.filter_by(user_id=current_user.id).all()
        return render_template("about.html", user_question_sets=user_question_sets)
    else:
        return redirect(url_for("register"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user)
            flash("You have been logged in successfully!", "success")
            return redirect(request.args.get("next") or url_for("home"))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data,
            email=form.email.data,
            password=form.password.data,
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully!", "success")
    return redirect(url_for("home"))


@app.route("/public_sets")
def public_sets():
    question_sets = QuestionSet.query.filter_by(private=False).all()
    return render_template("public_questions.html", question_sets=question_sets)


@app.route("/private_sets")
@login_required
def private_sets():
    question_sets = QuestionSet.query.filter_by(user_id=current_user.id).all()
    return render_template("private_sets.html", question_sets=question_sets)


@app.route("/create_question_set", methods=["GET", "POST"])
@login_required
def create_question_set():
    form = QuestionSetForm()
    if form.validate_on_submit():
        title = form.title.data
        private = form.private.data
        label = form.label.data
        question_1 = form.question_1.data
        question_2 = form.question_2.data
        question_3 = form.question_3.data
        question_4 = form.question_4.data
        question_5 = form.question_5.data
        question_set = QuestionSet(
            title=title,
            private=private,
            label=label,
            question_1=question_1,
            question_2=question_2,
            question_3=question_3,
            question_4=question_4,
            question_5=question_5,
            user=current_user,
        )
        db.session.add(question_set)
        db.session.commit()
        flash("Your question set has been created!", "success")
        return redirect(url_for("home"))
    return render_template(
        "create_question_set.html", title="Create Question Set", form=form
    )


@app.route("/question_sets")
def question_sets():
    question_sets = QuestionSet.query.all()
    return render_template("question_sets.html", question_sets=question_sets)


@app.route("/question_set/<int:id>")
def question_set(id):
    question_set = QuestionSet.query.get_or_404(id)
    return render_template("question_set.html", question_set=question_set)


"""
@app.route('/interview/<int:id>', methods=['GET', 'POST'])
def interview(id):
    if request.method == 'GET':
        return render_template('interview.html', id=id)
    elif request.method == 'POST':
        # Get interview ID and start interview input
        interview_id = request.form.get('id')
        start_interview = request.form.get('start_interview')

        if start_interview.lower() == 'yes':
            # Set up video recording
            cap = cv2.VideoCapture(0)  # 0 is the index of the default camera
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_video = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))

            # Set up audio recording
            audio = pyaudio.PyAudio()
            stream = audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
            frames = []

            # Ask questions and record video and audio
            questions = get_question_set_questions(interview_id)
            print(questions)
            for question in questions:
                speak(question)
                for i in range(30):  # Record for 30 seconds
                    ret, frame = cap.read()
                    out_video.write(frame)
                    data = stream.read(1024)
                    frames.append(data)

            # End the interview and save the recording
            out_video.release()
            cap.release()
            stream.stop_stream()

            # Save the audio and video files separately
            output_dir = 'static/'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            waveFile = wave.open(output_dir+'output.wav', 'wb')
            waveFile.setnchannels(1)
            waveFile.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            waveFile.setframerate(44100)
            waveFile.writeframes(b''.join(frames))
            waveFile.close()

            # Combine audio and video files
            video_clip = VideoFileClip('output.avi')
            audio_clip = AudioFileClip(output_dir + 'output.wav')
            audio_clip = audio_clip.set_start(0)
            final_clip = CompositeVideoClip([video_clip.set_audio(audio_clip)])
            final_clip.write_videofile(output_dir + 'output.mp4', fps=20, codec='libx264', audio_codec='aac')

            os.remove('output.avi')
            os.remove(output_dir+'output.wav')
            return redirect('/play_recorded_video')

        else:
            return render_template('interview.html', id=interview_id, message='Interview aborted.')

"""

import os
import wave
import cv2
import pyaudio
import pyttsx3

from moviepy.editor import *

global cap
cap = None


@app.route("/video_feed")
def video_feed():
    global cap
    cap = cv2.VideoCapture(0)
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )



def turn_off_video_feed():
    global cap
    if cap is not None:
        cap.release()  # Release the video capture object
        cap = None
    print("Video feed turned off")
def generate_frames():
    global cap
    while True:
        success, frame = cap.read()  # read the camera frame
        if not success:
            break
        else:
            # encode the frame in JPEG format
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()

            # yield the frame in the byte format
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


import time


def get_questions(id):
    question_set = QuestionSet.query.filter_by(id=id).first()
    if not question_set:
        return None
    return [
        question_set.question_1,
        question_set.question_2,
        question_set.question_3,
        question_set.question_4,
        question_set.question_5,
    ]


@app.route("/hi/<int:id>", methods=["GET", "POST"])
def hi(id):
    questions = get_questions(id)
    return str(questions)


@app.route("/interview/<int:id>", methods=["GET", "POST"])
@login_required
def interview(id):
    question_set = QuestionSet.query.get(id)

    if question_set is None:
        return render_template("error.html", message="Question Set Not Available")

    if request.method == "GET":
        return render_template("interview.html", question_set=question_set)
    elif request.method == "POST":
        start_interview = request.form.get("start_interview")

        try:
            asyncio.get_event_loop()
        except RuntimeError:
            pass  # Event loop already running, ignore
        else:
            # Set up event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            # Set up video recording
            cap = cv2.VideoCapture(0)  # 0 is the index of the default camera
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out_video = cv2.VideoWriter("output.avi", fourcc, 20.0, (640, 480))

            # Set up audio recording
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024,
            )
            frames = []

            # Set up text writing on video
            font = cv2.FONT_HERSHEY_SIMPLEX
            bottom_left_corner = (10, 400)
            font_scale = 1
            font_color = (255, 255, 255)
            line_type = 2

            # Ask questions and record video and audio
            questions = get_questions(id)
            print(questions)
            for question in questions:
                speak(question)
                for i in range(300):  # Record for 30 seconds
                    ret, frame = cap.read()
                    cv2.putText(
                        frame,
                        question,
                        bottom_left_corner,
                        font,
                        font_scale,
                        font_color,
                        line_type,
                    )
                    out_video.write(frame)
                    data = stream.read(1024)
                    frames.append(data)

            # End the interview and save the recording
            out_video.release()
            cap.release()
            stream.stop_stream()

            # Save the audio and video files separately
            output_dir = "static/"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            waveFile = wave.open(output_dir + "output.wav", "wb")
            waveFile.setnchannels(1)
            waveFile.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            waveFile.setframerate(44100)
            waveFile.writeframes(b"".join(frames))
            waveFile.close()

            # Combine audio and video files
            video_clip = VideoFileClip("output.avi")
            audio_clip = AudioFileClip(output_dir + "output.wav")
            audio_clip = audio_clip.set_start(0)
            final_clip = video_clip.set_audio(audio_clip)
            final_clip.write_videofile(
                output_dir + "output.mp4", fps=20, codec="libx264", audio_codec="aac"
            )
            os.remove("output.avi")
            os.remove(output_dir + "output.wav")

            return redirect("/play_recorded_video")
        except Exception as e:
            # Handle the exception
            error_message = "An error occurred during the interview process: {}".format(
                str(e)
            )
            return render_template("error.html", message=error_message)


@app.route("/play_recorded_video", methods=["GET"])
def play_recorded_video():
    video_file = "static/output.mp4"
    return render_template("play_recorded_video.html", video_file=video_file)


if __name__ == "__main__":
    app.run(debug=True)

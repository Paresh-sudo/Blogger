import secrets,os
from PIL import Image
from datetime import datetime
from flask import render_template, url_for, flash, redirect,request,abort
from flaskblog import app,db,bcrypt,mail
from flaskblog.forms import RegistrationForm, LoginForm , UpdationForm ,PostForm,RequestResetForm, ResetPasswordForm
from flaskblog.models import User, Post
from flask_login import login_user,current_user,logout_user,login_required
from flask_mail import Message



@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page,per_page=3)# for paginate query posts.items in home.html
    #posts = Post.query.all() #for simple query 
    #print(posts)
    return render_template('home.html', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hash_pwd = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username = form.username.data, email = form.email.data,password = hash_pwd)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data} you ca login now!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user,remember = form.remember.data)
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

#save picture in profile_pics

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename) #_ is f_name for uses not required so in python use this for that not needed
    picture_fun = random_hex + f_ext
    print(picture_fun)
    picture_path = os.path.join(app.root_path,'static/profile_pics/',picture_fun)
    #print(picture_path)
    output_size = (125,125)
    i = Image.open(form_picture)

    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fun


@app.route("/account",methods=['GET','POST'])
@login_required
def account():
    posts = Post.query.filter_by(author=current_user).all() # user all post
    form = UpdationForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file  = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your Account is update!','success')
        return redirect(url_for('account'))
    elif request.method =="GET":
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static',filename='profile_pics/'+current_user.image_file)
    return render_template('account.html',title='Account',image_file=image_file,form=form,posts=posts)

#for crete post
@app.route("/post/new",methods=['GET','POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data,content = form.content.data, author = current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your content is created!','success')
        return redirect(url_for('home'))
    return render_template('new_post.html',title='Post',form=form, legend='New Post')

@app.route("/view_post/<int:post_id>")
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('view_post.html',title='post.title',post = post ) 

@app.route("/view_post/<int:post_id>/update",methods=["GET","POST"])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    print(post)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.date_posted = datetime.utcnow() #time upadte on update data
        db.session.commit()
        flash('Your content is Updated!','success')
        return redirect(url_for('view_post',post_id = post.id))
    elif request.method=="GET":
        form.title.data=post.title
        form.content.data=post.content

    return render_template('new_post.html',title='Update post',form = form , legend='Update Post')

@app.route("/view_post/<int:post_id>/delete",methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been Deleted!','success')
    return redirect(url_for('home')) 

@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page',1,type=int)
    user = User.query.filter_by(username = username).first_or_404()
    posts = Post.query.filter_by(author=user)\
            .order_by(Post.date_posted.desc())\
            .paginate(page=page,per_page=3)# for paginate query posts.items in home.html
    
    return render_template('user_posts.html', posts=posts , user = user)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for,send_from_directory
from werkzeug.utils import secure_filename

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt"}

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- CREATE TABLES ----------------
def create_tables():
    conn = get_db()

    # Users table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # Notices table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        department TEXT,
        category TEXT,
        priority TEXT,
        role TEXT,
        filename TEXT,
        link TEXT,
        
        views INTEGER DEFAULT 0
    )
    """)

    # Default users
    conn.execute("INSERT OR IGNORE INTO users (username,password,role) VALUES ('admin','123','Admin')")
    conn.execute("INSERT OR IGNORE INTO users (username,password,role) VALUES ('hodcse','123','HOD')")
    conn.execute("INSERT OR IGNORE INTO users (username,password,role) VALUES ('faculty1','123','Faculty')")

    conn.commit()
    conn.close()

# Call once on start
create_tables()
# ============================
# ---------------- EXAM CELL DASHBOARD ----------------
@app.route("/exam/<dept>", methods=["GET", "POST"])
def exam_dashboard(dept):
    conn = get_db()
    categories = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        filename = None
        file = request.files.get("file")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn.execute(
            "INSERT INTO notices (title, content, department, category, role, filename) VALUES (?, ?, ?, ?, ?, ?)",
            (title, content, dept.upper(), category, "ExamCell", filename)
        )
        conn.commit()
        return redirect(url_for("exam_dashboard", dept=dept))

    notices = conn.execute(
        "SELECT * FROM notices WHERE department=? AND role='ExamCell' ORDER BY id DESC",
        (dept.upper(),)
    ).fetchall()
    conn.close()
    return render_template("exam_notices.html", dept=dept.upper(), notices=notices, categories=categories)
@app.route("/exam")
def exam_home():
    departments = ["CSE", "ECE", "EEE", "CIVIL", "MECH"]
    return render_template("exam_home.html", departments=departments)

# ---------------- VIEW ----------------
@app.route("/exam/<dept>/view/<int:notice_id>")
def exam_view_notice(dept, notice_id):
    conn = get_db()
    notice = conn.execute("SELECT * FROM notices WHERE id=?", (notice_id,)).fetchone()
    if notice:
        conn.execute("UPDATE notices SET views = views + 1 WHERE id=?", (notice_id,))
        conn.commit()
    conn.close()
    return render_template("exam_view_notice.html", notice=notice, dept=dept)

# ---------------- EDIT ----------------
@app.route("/exam/<dept>/edit/<int:notice_id>", methods=["GET", "POST"])
def exam_edit_notice(dept, notice_id):
    conn = get_db()
    notice = conn.execute("SELECT * FROM notices WHERE id=?", (notice_id,)).fetchone()

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        filename = notice["filename"]

        file = request.files.get("file")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn.execute(
            "UPDATE notices SET title=?, content=?, category=?, filename=? WHERE id=?",
            (title, content, category, filename, notice_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("exam_dashboard", dept=dept))

    conn.close()
    categories = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
    return render_template("exam_edit_notice.html", notice=notice, dept=dept, categories=categories)

# ---------------- DELETE ----------------
@app.route("/exam/<dept>/delete/<int:notice_id>")
def exam_delete_notice(dept, notice_id):
    conn = get_db()
    notice = conn.execute("SELECT * FROM notices WHERE id=?", (notice_id,)).fetchone()
    if notice["filename"]:
        path = os.path.join(app.config["UPLOAD_FOLDER"], notice["filename"])
        if os.path.exists(path):
            os.remove(path)
    conn.execute("DELETE FROM notices WHERE id=?", (notice_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("exam_dashboard", dept=dept))


   
# ================= ADMIN / EXAM / PLACEMENT UPLOAD =================
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        role = request.form["role"]
        file = request.files["file"]

        filename = ""
        if file:
            filename = file.filename
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("database.db")
        conn.execute(
            "INSERT INTO notices (title, content, role, filename) VALUES (?, ?, ?, ?)",
            (title, content, role, filename)
        )
        conn.commit()
        conn.close()

        return redirect("/upload")

    return render_template("upload.html")

# ================= STUDENT VIEW =================


# ================= PDF OPEN =================
@app.route("/uploads/<filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student")
def student_dashboard():
    conn = get_db()

    admin_notices = conn.execute(
        "SELECT * FROM notices WHERE role='Admin' ORDER BY id DESC"
    ).fetchall()

    exam_notices = conn.execute(
        "SELECT * FROM notices WHERE role='ExamCell' ORDER BY id DESC"
    ).fetchall()

    placement_notices = conn.execute(
        "SELECT * FROM notices WHERE role='Placement' ORDER BY id DESC"
    ).fetchall()

    hod_notices = conn.execute(
        "SELECT * FROM notices WHERE role='HOD' ORDER BY id DESC"
    ).fetchall()

    faculty_notices = conn.execute(
        "SELECT * FROM notices WHERE role='Faculty' ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "student_dashboard.html",
        admin_notices=admin_notices,
        exam_notices=exam_notices,
        placement_notices=placement_notices,
        hod_notices=hod_notices,
        faculty_notices=faculty_notices
    )   
# ---------------- SERVE UPLOADED FILES ----------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

          
       
# ---------------- HOME PAGE ----------------
@app.route("/")
def home_page():
    return render_template("home.html")

# ---------------- ADMIN PAGE ----------------


# ---------------- DEPARTMENTS PAGE ----------------
@app.route("/departments")
def departments_page():
    return render_template("departments.html")

# ---------------- DEPARTMENT ROLES PAGE ----------------
@app.route("/department/<dept>")
def department_roles_page(dept):
    return render_template("roles.html", dept=dept)

# ---------------- PLACEMENT CELL PAGE ----------------
# Main placement page (3 cards)
@app.route("/placement")
def placement_home():
    return render_template("placement.html", section=None)

# Specific section route

    



# ---------------- HOD DASHBOARD ----------------
@app.route("/hod/<dept>", methods=["GET", "POST"])
def hod_dashboard(dept):
    conn = get_db()

    if request.method=="POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        priority = request.form["priority"]
        role = "HOD"
        filename = None

        # File upload
        if "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn.execute(
            "INSERT INTO notices (title, content, department, category, priority, role, filename) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, content, dept, category, priority, role, filename)
        )
        conn.commit()

    notices = conn.execute(
        "SELECT * FROM notices WHERE department=? ORDER BY id DESC",(dept,)
    ).fetchall()
    conn.close()
    return render_template("hod_dashboard.html", dept=dept, notices=notices)
@app.route("/placement/<section>", methods=["GET","POST"])
def placement_section_dashboard(section):
    conn = get_db()
    if request.method=="POST":
        title = request.form["title"]
        content = request.form["content"]
        filename = None
        if "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        conn.execute(
            "INSERT INTO notices (title, content, category, role, filename) VALUES (?, ?, ?, ?, ?)",
            (title, content, section, "Placement", filename)
        )
        conn.commit()
    notices = conn.execute(
        "SELECT * FROM notices WHERE category=? AND role='Placement' ORDER BY id DESC",(section,)
    ).fetchall()
    conn.close()
    return render_template("placement_dashboard.html", section=section, notices=notices)
@app.route("/placement/<section>/edit/<int:notice_id>", methods=["GET","POST"])
def placement_edit_notice(section, notice_id):
    conn = get_db()
    notice = conn.execute(
        "SELECT * FROM notices WHERE id=? AND category=? AND role='Placement'", 
        (notice_id, section)
    ).fetchone()

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        filename = notice["filename"]

        if "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn.execute(
            "UPDATE notices SET title=?, content=?, filename=? WHERE id=?",
            (title, content, filename, notice_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("placement_section_dashboard", section=section))

    conn.close()
    return render_template("placement_edit_notice.html", notice=notice, section=section)
# ---------------- DELETE NOTICE FOR PLACEMENT ----------------
@app.route("/placement/<section>/delete/<int:notice_id>")
def placement_delete_notice(section, notice_id):
    conn = get_db()
    # Delete file first if exists
    notice = conn.execute("SELECT filename FROM notices WHERE id=? AND category=?", (notice_id, section)).fetchone()
    if notice and notice["filename"]:
        path = os.path.join(app.config["UPLOAD_FOLDER"], notice["filename"])
        if os.path.exists(path):
            os.remove(path)
    # Delete from DB
    conn.execute("DELETE FROM notices WHERE id=? AND category=?", (notice_id, section))
    conn.commit()
    conn.close()
    return redirect(url_for("placement_section_dashboard", section=section))
# ---------------- VIEW NOTICE FOR PLACEMENT ----------------
@app.route("/placement/<section>/view/<int:notice_id>")
def placement_view_notice(section, notice_id):
    conn = get_db()
    notice = conn.execute(
        "SELECT * FROM notices WHERE id=? AND category=? AND role='Placement'",
        (notice_id, section)
    ).fetchone()
    conn.close()
    return render_template("placement_view_notice.html", notice=notice, section=section)

# ---------------- FACULTY DASHBOARD ----------------
@app.route("/faculty/<dept>", methods=["GET","POST"])
def faculty_dashboard(dept):
    conn = get_db()
    if request.method=="POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        priority = request.form["priority"]
        role = "Faculty"
        filename = None
        if "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        conn.execute(
            "INSERT INTO notices (title, content, department, category, priority, role, filename) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, content, dept, category, priority, role, filename)
        )
        conn.commit()
    notices = conn.execute(
        "SELECT * FROM notices WHERE department=? AND role='Faculty' ORDER BY id DESC",(dept,)
    ).fetchall()
    conn.close()
    return render_template("faculty_dashboard.html", dept=dept, notices=notices)

# ---------------- EDIT NOTICE FOR FACULTY ----------------
@app.route("/faculty/<dept>/edit/<int:notice_id>", methods=["GET","POST"])
def faculty_edit_notice(dept, notice_id):
    conn = get_db()
    notice = conn.execute("SELECT * FROM notices WHERE id=?",(notice_id,)).fetchone()
    if request.method=="POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        priority = request.form["priority"]
        # FILE UPDATE IF NEW FILE SELECTED
        if "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                conn.execute(
                    "UPDATE notices SET title=?, content=?, category=?, priority=?, filename=? WHERE id=?",
                    (title, content, category, priority, filename, notice_id)
                )
            else:
                conn.execute(
                    "UPDATE notices SET title=?, content=?, category=?, priority=? WHERE id=?",
                    (title, content, category, priority, notice_id)
                )
        else:
            conn.execute(
                "UPDATE notices SET title=?, content=?, category=?, priority=? WHERE id=?",
                (title, content, category, priority, notice_id)
            )
        conn.commit()
        conn.close()
        return redirect(f"/faculty/{dept}")
    conn.close()
    return render_template("faculty_edit_notice.html", notice=notice, dept=dept)

# ---------------- DELETE NOTICE FOR FACULTY ----------------
@app.route("/faculty/<dept>/delete/<int:notice_id>")
def faculty_delete_notice(dept, notice_id):
    conn = get_db()
    conn.execute("DELETE FROM notices WHERE id=?",(notice_id,))
    conn.commit()
    conn.close()
    return redirect(f"/faculty/{dept}")

# ---------------- VIEW NOTICE FOR FACULTY ----------------
@app.route("/faculty/<dept>/view/<int:notice_id>")
def faculty_view_notice(dept, notice_id):
    conn = get_db()
    notice = conn.execute("SELECT * FROM notices WHERE id=?",(notice_id,)).fetchone()
    conn.close()
    return render_template("faculty_view_notice.html", notice=notice, dept=dept)



        

# ---------------- VIEW NOTICE ----------------
@app.route("/hod/<dept>/view/<int:notice_id>")
def view_notice(dept, notice_id):
    conn = get_db()
    notice = conn.execute("SELECT * FROM notices WHERE id=?",(notice_id,)).fetchone()
    conn.close()
    return render_template("view_notice.html", notice=notice, dept=dept)

# ---------------- EDIT NOTICE ----------------
@app.route("/hod/<dept>/edit/<int:notice_id>", methods=["GET","POST"])
def edit_notice(dept, notice_id):
    conn = get_db()
    notice = conn.execute("SELECT * FROM notices WHERE id=?",(notice_id,)).fetchone()

    if request.method=="POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        priority = request.form["priority"]
        filename = notice["filename"]

        # File update if new file uploaded
        if "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn.execute(
            "UPDATE notices SET title=?, content=?, category=?, priority=?, filename=? WHERE id=?",
            (title, content, category, priority, filename, notice_id)
        )
        conn.commit()
        conn.close()
        return redirect(f"/hod/{dept}")

    conn.close()
    return render_template("edit_notice.html", notice=notice, dept=dept)

# ---------------- DELETE NOTICE ----------------
@app.route("/hod/<dept>/delete/<int:notice_id>")
def delete_notice(dept, notice_id):
    conn = get_db()
    conn.execute("DELETE FROM notices WHERE id=?",(notice_id,))
    conn.commit()
    conn.close()
    return redirect(f"/hod/{dept}")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin_page():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notices ORDER BY id DESC")
    notices = cur.fetchall()
    conn.close()
    return render_template("admin.html", notices=notices)

# ---------------- ADD NOTICE ----------------
@app.route("/admin/add_notice", methods=["POST"])
def admin_add_notice():
    title = request.form["title"]
    content = request.form["content"]
    category = request.form["category"]
    link = request.form.get("link")
    file = request.files.get("file")
    filename = None

    if file and file.filename != "":
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    conn = get_db()
    conn.execute("""
        INSERT INTO notices (title, content, category, link, filename)
        VALUES (?, ?, ?, ?, ?)
    """, (title, content, category, link, filename))
    conn.commit()
    conn.close()
    return redirect("/admin")

# ---------------- DELETE NOTICE ----------------
@app.route("/admin/delete/<int:id>")
def admin_delete_notice(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT filename FROM notices WHERE id=?", (id,))
    file = cur.fetchone()
    if file and file["filename"]:
        path = os.path.join(app.config["UPLOAD_FOLDER"], file["filename"])
        if os.path.exists(path):
            os.remove(path)
    cur.execute("DELETE FROM notices WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/admin")  
@app.route("/admin/view/<int:id>")
def admin_view_notice(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notices WHERE id=?", (id,))
    notice = cur.fetchone()
    conn.close()
    if not notice:
        return "Notice not found", 404
    return render_template("admin_view_notice.html", notice=notice)
# ---------------- EDIT NOTICE ----------------
@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def admin_edit_notice(id):
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        link = request.form.get("link")
        file = request.files.get("file")
        filename = None
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            cur.execute("""
                UPDATE notices SET title=?, content=?, category=?, link=?, filename=? WHERE id=?
            """, (title, content, category, link, filename, id))
        else:
            cur.execute("""
                UPDATE notices SET title=?, content=?, category=?, link=? WHERE id=?
            """, (title, content, category, link, id))
        conn.commit()
        conn.close()
        return redirect("/admin")
    cur.execute("SELECT * FROM notices WHERE id=?", (id,))
    notice = cur.fetchone()
    conn.close()
    return render_template("edit.html", notice=notice)  
# ---------------- DELETE NOTICE ----------------
@app.route("/delete/<int:id>")
def hod_delete_notice(id):
    conn = get_db()
    cur = conn.cursor()

    # Delete file first if exists
    cur.execute("SELECT filename FROM notices WHERE id=?", (id,))
    file = cur.fetchone()
    if file and file["filename"]:
        path = os.path.join(app.config["UPLOAD_FOLDER"], file["filename"])
        if os.path.exists(path):
            os.remove(path)

    cur.execute("DELETE FROM notices WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

# ---------------- EDIT NOTICE PAGE ----------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def hod_edit_notice(id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        link = request.form.get("link")
        filename = None

        file = request.files.get("file")
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            cur.execute("""
                UPDATE notices SET title=?, content=?, category=?, link=?, filename=? WHERE id=?
            """, (title, content, category, link, filename, id))
        else:
            cur.execute("""
                UPDATE notices SET title=?, content=?, category=?, link=? WHERE id=?
            """, (title, content, category, link, id))

        conn.commit()
        conn.close()
        return redirect("/")

    cur.execute("SELECT * FROM notices WHERE id=?", (id,))
    notice = cur.fetchone()
    conn.close()
    return render_template("edit.html", notice=notice)

# ---------------- SERVE UPLOADED FILES ----------------
@app.route("/uploads/<filename>")
def uploaded_file_view(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ---------------- LOGOUT (Dummy) ----------------
@app.route("/logout")
def logout():
    return redirect("/")    
# ---------------- RUN APP ----------------
if __name__=="__main__":
    app.run(debug=True)
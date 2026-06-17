from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy.orm import Session

from database import get_engine, lookup_representative, get_member_category_scores

from models import Member

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        zip_code = request.form["zip_code"]

        # Get house represenative from zip code
        result = lookup_representative(zip_code)
        
        if "error" in result[0]:
            return render_template("home.html", error=result[0]["error"])
        
        if "vacant" in result[0]:
            return render_template("home.html", error=result[0]["message"])
         
        return render_template("results.html", members=result)
    
    return render_template("home.html")

@app.route("/member/<member_id>")
def member_profile(member_id):
    engine = get_engine()
    with Session (engine) as session:
        member = session.get(Member, member_id)

        member_category_scores = get_member_category_scores(member_id)
        print(member_category_scores)

    return render_template("member.html", member=member, scores=member_category_scores)

if __name__ == "__main__":
    app.run(debug=True)
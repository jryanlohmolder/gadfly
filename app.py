from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy.orm import Session

from anthropic_api import PARSE_BILL_PROMPT, SYNTHESIZE_CHUNKS_PROMPT
from database import get_engine, lookup_representative, get_member_category_scores
from models import Member

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    """
    Handle the home page and zip code form submission.
    
    GET: Render the home page with the zip code form.
    
    POST: Look up representatives for the submitted zip code.
          Redirects to results page on success, or renders
          home page with error message on failure.
    """
    
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
    """
    Render the voting profile page for a single member.
    
    Args:
        member_id (str): Bioguide ID of the member.
    """
    
    engine = get_engine()
    with Session (engine) as session:
        member = session.get(Member, member_id)

        member_category_scores = get_member_category_scores(member_id)
        print(member_category_scores)

    return render_template("member.html", member=member, scores=member_category_scores)

@app.route("/about")
def about_page():
    """Render the about page."""
    
    return render_template("about.html", prompt=PARSE_BILL_PROMPT, prompt_2=SYNTHESIZE_CHUNKS_PROMPT)

@app.route("/prompts")
def prompt_page():
    """Render the prompt page displaying the bill analysis prompt."""
   
    return render_template("prompts.html", prompt=PARSE_BILL_PROMPT, prompt_2=SYNTHESIZE_CHUNKS_PROMPT)

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, flash, request, redirect, url_for, render_template
import os
import json
from dotenv import load_dotenv  
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains import SequentialChain
import traceback
import pandas as pd
from langchain.callbacks import get_openai_callback
from utils import  RESPONSE_JSON
import PyPDF2

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

OPENAI_API_KEY=api_key

f = ""
mode = ""
noq = 0
question = []
correct =[]
options = []
submittedans = []


app = Flask(__name__)
 
# home route that returns below text when root url is accessed
@app.route("/", methods = ['GET','POST'])
def home():
    if request.method == 'POST':
        global f,noq,mode
        print('hi')
        f = request.files['file'] 
        noq = request.form.get('noq')
        mode = request.form.get('mode')
        f.save("file.pdf") 
        print(f,noq,mode)
        return redirect('/response')
    return render_template("index.html") 

"""@app.route('/respon')
def hello_r():
    print(f,noq,mode)
    return "Success"
"""

@app.route("/response")
def hello_world():
    llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0, max_tokens=-1)
    print(llm)
    template = """
    Text: {text}
    You are an expert MCQ maker. Given the above text, it is your job to\
    create a quiz of {number} multiple choice questions for user in {mode} tone.
    Make sure that questions are not repeated and check all the questions to be conforming to the text as well.
    Make sure to format your response like the RESPONSE_JSON below and use it as a guide.\
    Ensure to make the {number} MCQs.
    ### RESPONSE_JSON
    {response_json}
    """
    quiz_generation_prompt = PromptTemplate(
    input_variables=["text", "number", "mode", "response_json"],
    template=template,
    )
    quiz_chain = LLMChain(
    llm=llm, prompt=quiz_generation_prompt, output_key="quiz", verbose=True
    )

# This is an LLMChain to evaluate the multiple choice questions created by the above chain
    llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0)
    template = """You are an expert english grammarian and writer. Given a multiple choice quiz for  User.\
    You need to evaluate complexity of the questions and give a complete analysis of the quiz if the students 
    will be able to understand the questions and answer them. Only use at max 50 words for complexity analysis.
    If quiz is not at par with the cognitive and analytical abilities of the students,\
    update the quiz questions which need to be changed and change the tone such that it perfectly fits the students abilities. 
    Quiz MCQs:
    {quiz}
    Critique from an expert english writer of the above quiz:"""

    quiz_evaluation_prompt = PromptTemplate(
        input_variables=["quiz"], template=template
    )
    

# This is the overall chain where we run these two chains in sequence.
    generate_evaluate_chain = SequentialChain(
    chains=[quiz_chain],
    input_variables=["text", "number", "mode", "response_json"],
    # Here we return multiple variables
    output_variables=["quiz"],
    verbose=True,
    )

    file = ('file.pdf')
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
            
    response = generate_evaluate_chain(
                    {
                        "text": text,
                        "number": noq,
                        "mode": mode,
                        "response_json": json.dumps(RESPONSE_JSON),
                    }
                )
    test_string = response["quiz"]
    res = json.loads(test_string)
    global question,options,correct
    for i in res.keys():
        for j in res[i].keys():
            if j=="mcq":
                question.append(res[i][j])
            if j=="correct":
                correct.append(res[i][j])
            if j=="options":
                options.append(res[i][j])
    print(question)
    print(correct)
    print(options)
    return redirect('/quiz')

@app.route("/quiz", methods = ['GET','POST'])
def quiz():
    global question,correct,options,submittedans
    if request.method == 'POST':
        print("correct")
        submittedans=[]
        for i in range(0,len(correct)):
            submittedans.append(request.form.get(str(i)))
        print(submittedans)
        return redirect('/result')
    return render_template("quiz.html",question=question,len=len(question),correct=correct,option=options)

@app.route("/result")
def res():
    score = 0
    count=0
    for i in range(0,len(correct)):
        if correct[i]==submittedans[i]:
            score = score +1
        count=len(correct)
    val=""
    wval=(100*score)/count
    if wval>=70:
        pgvalue="success"
    elif wval>50:
        pgvalue="warning"
    else:
        pgvalue="danger"
    if score>=count/2:
        val="Pass"
        color="green"
    else:
        val="Fail"
        color="red"
    return render_template('result.html',score=score,i=count,val=val,col=color,wval=wval,pgvalue=pgvalue)

if __name__ == '__main__': 
    app.run()
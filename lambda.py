from dataclasses import replace
from fileinput import filename
from fastapi.responses import HTMLResponse
from urllib.parse import unquote_plus
from starlette.responses import FileResponse 
# from helper import process_error, extract_kv, extract_lineitems, convert_to_image
from typing import Optional
from fastapi import FastAPI, Body, Request, Form
from fastapi import FastAPI, File, UploadFile
from starlette.background import BackgroundTask
from fastapi.templating import Jinja2Templates
import os
import glob
import pandas as pd

from main import main


app = FastAPI()
templates = Jinja2Templates(directory="htmldirectory")
@app.get("/")
async def read_index():
    return FileResponse('./index.html')


@app.post("/filesend")
def lambda_handler(request: Request,file: UploadFile):
    path = f"./temp/{file.filename}"
    ot_path=""
    
    with open(path, "wb+") as file_object:

        file_object.write(file.file.read())
    
            
    try:
        print('try')
        event = True

    except:
        event = None

    if event:
        try:
            print(file.content_type)
            if file.content_type=='image/jpeg':
                ot_path , ot_text = main(path, output_dir = r"new_results",confidence=0.7)
                print(ot_path,ot_text)
              


            else:

                print("Exception")
               
            
            html_content = f"""
                    <html>
                        <head>
                            <title>Results</title>
                        </head>
                        <body>
                            <h1>{ot_path}</h1>
                            <h2>{ot_text}</h2>
                        </body>
                    </html>
                    """

            # html_content = """
            #         <html>
            #             <head>
            #                 <title>Error in file</title>
            #             </head>
            #             <body>
            #                 <h1>Execution Complete</h1>
            #             </body>
            #         </html>
            #         """
       
        
            # return FileResponse('./htmldirectory/df_representation.html')
            return HTMLResponse(content=html_content, status_code=200)

            
            

        except Exception as e:
            files = glob.glob(f"temp/{file.filename}")
            for f in files:
                os.chmod(f, 0o777)
                try:
                    os.remove(f)
                except OSError:
                    pass
          
            html_content = """
                    <html>
                        <head>
                            <title>Error in file</title>
                        </head>
                        <body>
                            <h1>Cannot upload the file, please try again</h1>
                        </body>
                    </html>
                    """
       
        
            # return FileResponse('./htmldirectory/df_representation.html')
            return HTMLResponse(content=html_content, status_code=200)
            
            

    return templates.TemplateResponse(
        'index.html',
        {'request': request, 'data': 'uploaded'})



    



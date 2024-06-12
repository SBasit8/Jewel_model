import os
import glob
from flask import Flask, flash, request, redirect, url_for, send_from_directory, render_template_string
from werkzeug.utils import secure_filename
from main import main

UPLOAD_FOLDER = './temp'
ALLOWED_EXTENSIONS = { 'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'supersecretkey'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
<html>
  <body>
    <h1>OCR results on documents</h1>
    <form method="post" id="myForm" enctype="multipart/form-data" action="/filesend">
      <input id="image" type="file" name="files" multiple required/>

      <p style="display: inline"><b>* Cannot be null</b></p>
      <br /><br />
      <input type="submit" value="Search" />
    </form>

    <div id="responseArea"></div>

    <script>
      function submitForm() {
        var formElement = document.getElementById("myForm");
        var data = new FormData(formElement);
        fetch("/filesend", {
          method: "POST",
          body: data,
        })
          .then((resp) => resp.text()) // or, resp.json(), etc.
          .then((data) => {
            document.getElementById("responseArea").innerHTML = data;
          })
          .catch((error) => {
            console.error(error);
          });
      }
    </script>
  </body>
</html>

    '''

@app.route('/filesend', methods=['POST'])
def upload_files():
    try:
        if 'files' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        files = request.files.getlist('files')
        
        if len(files) == 0:
            flash('No selected files')
            return redirect(request.url)
        
        results = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                try:
                    with open(file_path, "wb") as f:
                        f.write(file.read())
                except Exception as e:
                    results.append(("Error", f"Failed to save file {filename}: {str(e)}"))
                    continue
                
                try:
                    # Process the file
                    if file.content_type == 'image/jpeg':
                        ot_path, ot_text = main(file_path, output_dir="new_results", confidence=0.7)
                        results.append((ot_path, ot_text))
                    else:
                        results.append(("Error", f"Unsupported file type: {file.content_type}"))
                except Exception as e:
                    results.append(("Error", f"Failed to process file {filename}: {str(e)}"))
                    # Clean up the file if there was an error
                    try:
                        os.chmod(file_path, 0o777)
                        os.remove(file_path)
                    except Exception as cleanup_error:
                        results.append(("Error", f"Failed to clean up file {filename}: {str(cleanup_error)}"))
    
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
        return render_template_string(html_content, results=results)
    
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}", 500

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)

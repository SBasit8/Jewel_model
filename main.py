import os
import cv2
from ultralytics import YOLO
from uuid import uuid4
import argparse
import io
import json
import glob
from google.cloud import vision
from google.cloud.vision_v1 import types
import csv
import re
import sys
import numpy as np
from fuzzywuzzy import fuzz
import sqlite3
from qreader import QReader
import pandas as pd


def update_last_row_count(conn):
   
    cursor = conn.cursor()

    # Get the id of the last row
    cursor.execute('''SELECT MAX(rowid) FROM info''')
    last_row_id = cursor.fetchone()[0]

    # Update the count on the last row
    cursor.execute('''UPDATE info SET count = count + 1 WHERE rowid = ?''', (last_row_id,))

    # Commit the transaction
    conn.commit()

def scan(masked_image):
    qreader = QReader()

    # Use the detect_and_decode function to get the decoded QR data
    decoded_text = qreader.detect_and_decode(image=masked_image)
    print(decoded_text[0])
    return decoded_text[0]


# def insert_in_db_details_season_year(conn, val):
#     cursor = conn.cursor()
#     query = '''INSERT INTO details (Season_Year) VALUES (?)'''
#     cursor.execute(query,val)
#     conn.commit()

# def insert_in_db_details_season(conn, val):
#     cursor = conn.cursor()
#     query = '''INSERT INTO details (Season) VALUES (?)'''
#     cursor.execute(query,(val,))
#     conn.commit()    


def get_last_row_columns(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM info ORDER BY rowid DESC LIMIT 1 ")
    row = cursor.fetchone()
    if row:
       
        
        # Change the indices according to your table schema
        
        type_value = row[0]
        barcode_value = row[1]
        count_value= row[2]
        conn.commit()
        
        return type_value, barcode_value,count_value
    return None, None , None 

def insert_in_db_details(conn,val):
    cursor=conn.cursor()
    query='''INSERT INTO details(Barcode ,Length ,Weight ,Season ,Season_Year,Category ,Designer ,Date )
            VALUES(?,?,?,?,?,?,?,?) '''
    cursor.execute(query,val)
    print("Values inserted in details Table")
    

def insert_in_db(conn,values):

    cursor=conn.cursor()
    query='''INSERT INTO info (Type ,Barcode , count)
            VALUES(?,?,?)'''
    cursor.execute(query,values)
    

    print("Values inserted")
    get_query="SELECT * from info "
    cursor.execute(get_query)

    print(cursor.fetchall())
      
    conn.commit()
    
    # return cursor.lastrowid,values[0],values[1],values[2]

model = YOLO("jewelery_weight.pt") # model weights

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'iron-module-419322-91b0842f4a7b.json'
client = vision.ImageAnnotatorClient()


def detect_text(image):
    f_path=f"{uuid4()}.jpg"
    cv2.imwrite(f_path,image)
    """Detects text in the file."""
    client = vision.ImageAnnotatorClient()

    try:
        with open(f_path, 'rb') as image_file:
            content = image_file.read()
            
        
        #read image and get results
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        texts = response.text_annotations 
         
        
        for text in texts:
            
            print(text.description)
        if os.path.exists(f_path):
            os.remove(f_path)
            print("files deleted")
        else:
            print("file path does not exist")     
        return texts

                  
    except Exception as e :
        print("Error in",e)
        #print the error
        print("Error: ", sys.exc_info()[0])

# def contour(img_mask,img):
#         """Draw contour bounding and contour bounding box"""
       
#         contours, hierarchy = cv2.findContours(img_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#         img_contour = img.copy()
        
#         threshold_area=400
#         for idx, c in enumerate(contours):
#             # Skip small contours because its probably noise
#             if  cv2.contourArea(c) < threshold_area:
#                 continue

#             # Draw contour in red
#             cv2.drawContours(img_contour, contours, idx, (0, 0, 255), 2, cv2.LINE_4, hierarchy)
#         img_result = cv2.bitwise_and(img, img_contour)    
            

        # cv2.imshow('contour',img_result) 
        # cv2.waitKey(0)   
        # return img_result 

            
def match_regex(pattern, txt):
    # Compile the regex pattern
    regex = re.compile(pattern)
    print(regex)
    
    # Search for the pattern in the text
    mo = regex.search(txt)
    matches=mo.group()
    print(type(matches))
    print(matches)

    # matched_text=[match.group() for match in matches]
    # Return the match if found
    if matches:
        return matches
    else:
        return None

            

def mask_image(img):
    
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hsv_lower = np.array((0,20,20), np.uint8)  # Lower HSV value
    hsv_upper = np.array((70,255,255), np.uint8)  # Upper HSV value

    # Color segmentation with lower and upper threshold ranges to obtain a binary image
    img_mask = cv2.inRange(img_hsv, hsv_lower, hsv_upper)

    img_result = cv2.bitwise_and(img, img, mask=img_mask)
    return img_result     
        
def clear_database(conn):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM info')
    conn.commit()

def write_db_to_csv(conn, excel_file_path):
    cursor = conn.cursor()
    # cursor.execute('SELECT * FROM info')
    # rows = cursor.fetchall()
    
    # # Get column names from cursor description
    # column_names = [description[0] for description in cursor.description]

    # # Convert to DataFrame
    # df = pd.DataFrame(rows, columns=column_names)
    # # Write to Excel file
    # df.to_excel(excel_file_path, index=False)

    cursor.execute('SELECT * FROM info')
    info_rows = cursor.fetchall()
    info_columns = [description[0] for description in cursor.description]
    info_df = pd.DataFrame(info_rows, columns=info_columns)

    # Fetch and write data from 'details' table
    cursor.execute('SELECT * FROM details')
    details_rows = cursor.fetchall()
    details_columns = [description[0] for description in cursor.description]
    details_df = pd.DataFrame(details_rows, columns=details_columns)

    # Write to Excel file with multiple sheets
    with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
        info_df.to_excel(writer, sheet_name='Info', index=False)
        details_df.to_excel(writer, sheet_name='Details', index=False)
         


#  results of predtiction and Bounding Boxes


count=0
def prediction(image_path,output_dir,confidence,conn):
    global count 
    barcode_value=0
    output_path,output_text="",""
    filename,ext=os.path.splitext(image_path)
    if not (ext and (str(ext).lower() in [".png",".jpg",".jpeg"])):
        return "","invalid extension"
    image=cv2.imread(image_path)
    results = model.predict(image, conf=confidence)
    if results:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        classes = results[0].boxes.cls.cpu()
        prob = results[0].boxes.conf.cpu()
        output_text= []

      
      
        x=len(boxes)
        if x==0:
            return "","Empty Image"
        else:
            if x>1:
                    type="FRONT"
                    count=0 
                    sesn=None
                    yr=None 
                    date=None
                    length=None
                    weight=None
                    category=None
                    desi=None

                    for box,cls,con in zip(boxes,classes,prob):
                        x1,y1,x2,y2=box

                        crop=image[int(y1):int(y2),int(x1):int(x2)]
                

                        if model.names[int(cls)]!= 'jewelry':
                            masked_image=mask_image(crop) 
                            

                            if model.names[int(cls)] == 'config_1':


                            
                                sim_ocr=crop.copy()
                            
                                config_ocr=detect_text(sim_ocr) 
                                weight=0 
                                length=None  
                                for text in config_ocr:

                                    # print('\n"{}"'.format(text.description))
                                    vertices = (['({},{})'.format(vertex.x, vertex.y)
                                                for vertex in text.bounding_poly.vertices])
                                    
                                    # print(type(vertices))
                                    wx = [vertex.x for vertex in text.bounding_poly.vertices]
                                    wy = [vertex.y for vertex in text.bounding_poly.vertices]
                                    
                                    

                                                    
                                    # print('bounds: {}'.format(','.join(vertices)))
                                    # print('\n"{}"'.format(text.description))
                                    h,w,c=crop.shape
                                    xd=int(w)/2
                                    hi=int(h)/2
                                    # wx,y=vertices[2]

                                    num=re.findall("^\d+(\.\d+)?$|^\d+(\.\d+)?x10\d+$|^\d+\.$",text.description)
                                    
                                    if not len(num)==0 :

                                        if xd<wx[2]:
                                            length=text.description
                                            print(length)
                                            
                                        elif wy[2]<hi:
                                            
                                            weight=text.description
                                            print(weight)

                                output_text.append("{} : {}".format("Length",length)) 
                                output_text.append("{} : {}".format("Weight",weight)) 


                            else:
                                
                                sim_ocr=crop.copy()
                                config_ocr=detect_text(sim_ocr)
                                date=None
                                

                                for text in config_ocr:

                                    # print('\n"{}"'.format(text.description))
                                    # vertices = (['({},{})'.format(vertex.x, vertex.y)
                                    #             for vertex in text.bounding_poly.vertices])
                                
                                    d=re.findall('^\d.*24$',text.description)
                                    

                                    if not len(d)==0:
                                        
                                        date=text.description                   
                                        print(date)

                                output_text.append("{} : {}".format("DATE",date))      
                        else:
                            masked_image=crop.copy()



                        ocr_text=detect_text(masked_image)
                    
                    
                        if model.names[int(cls)]== 'jewelry':                 
                            
                            barcode_value=scan(masked_image)
                            print(barcode_value)

                            if not barcode_value:
                                
                                
                                for text in ocr_text:                
                            
                                    new_text=text.description.replace("BERNARDO","")
                                    new_text=new_text.replace("Bernardo","")
                                    new_text=new_text.replace("HandSample","")
                                    new_text=new_text.replace("In-HouseSample","")
                                    
                                    new_text=new_text.replace("Sample","")
                                    new_text=new_text.replace("Overseas","")
                                    new_text=new_text.replace("OverseasSample","")
                                    print(new_text)

                                    if len(new_text)>=6:

                                        x = re.findall("^\d{6,}$|^(?!(?:\d+|[A-Za-z]+)$)[A-Za-z0-9-]{1,}(?:[A-Za-z0-9-]{1,}){0,3}$", new_text)

                                    
                                        print(x)
                                        if x:
                                            new_barcode_value = x[0]
                                            barcode_found = False
                                            
                                            for i, entry in enumerate(output_text):
                                                if entry.startswith("Barcode :"):
                                                    old_value = entry.split(":")[1]
                                                    output_text[i] = "{} {}".format(entry, new_barcode_value)
                                                    barcode_found = True
                                                    barcode_value=old_value+new_barcode_value
                                                    break
                                            
                                            if not barcode_found:
                                                # output_text.append("Barcode : {}".format(new_barcode_value))
                                                barcode_value=new_barcode_value
                                

                            output_text.append("Barcode : {}".format(barcode_value))
                            filename=os.path.basename(image_path).split(".")[0]
                            cv2.imwrite(os.path.join(output_dir,f"{barcode_value}_CROP_{filename}.jpg"),crop)
                            
                            # for text in ocr_text:                
                                

                            #     new_text=text.description.replace("BERNARDO","")
                            #     new_text=new_text.replace("Bernardo","")
                            #     new_text=new_text.replace("HandSample","")
                            #     new_text=new_text.replace("In-HouseSample","")
                                
                            #     new_text=new_text.replace("Sample","")
                            #     new_text=new_text.replace("Overseas","")
                            #     new_text=new_text.replace("OverseasSample","")
                            #     print("ppppppppppppp",new_text)

                            #     if len(new_text)>=6:

                            #         x = re.findall("^\d{6,}$|^(?!(?:\d+|[A-Za-z]+)$)[A-Za-z0-9-]{1,}(?:[A-Za-z0-9-]{1,}){0,3}$", new_text)

                                
                            #         print(x)
                            #         if x:
                            #             new_barcode_value = x[0]
                            #             barcode_found = False
                                        
                            #             for i, entry in enumerate(output_text):
                            #                 if entry.startswith("Barcode :"):
                            #                     old_value = entry.split(":")[1]
                            #                     output_text[i] = "{} {}".format(entry, new_barcode_value)
                            #                     barcode_found = True
                            #                     barcode_value=old_value+new_barcode_value
                            #                     break
                                        
                            #             if not barcode_found:
                            #                 output_text.append("Barcode : {}".format(new_barcode_value))
                            #                 barcode_value=new_barcode_value

                                    # found_barcode = None
                                    # barcodes = []

                                    # # Iterate through the list and process barcode entries
                                    # for item in output_text:
                                    #     if item.startswith('Barcode'):
                                    #         if found_barcode is None:
                                    #             found_barcode = item  # Store the first Barcode entry
                                    #         else:
                                    #             # Append the new Barcode value to the existing one
                                    #             found_barcode += ', ' + item.split(': ')[1]
                                    #     else:
                                    #         barcodes.append(item)  # Add non-barcode items to a separate list

                                    # # If a Barcode was found, insert it at the beginning of the list
                                    # if found_barcode:
                                    #     barcodes.insert(0, found_barcode)

                                    # output_text = barcodes

                                    
                                


                                    

                                    # if not len(x)==0:
                                    #     output_text.append("{} : {}".format("Barcode",x[0]))
                                    #     barcode_value =x[0]
                                    #     # print(x[0]) 
                                    # print(output_text)
                                
                        
                            
                                    
                        else:
                            
                            if ocr_text:
                        
                                ocr_text_list=[]
                                        
                                if model.names[int(cls)]== 'config_2':
                                    for idx,text in enumerate(ocr_text):
                                        if idx!=0:
                                            ocr_text_list.append(text.description)
                                            
                                    # ocr_text_list.append(text.description)
                                    items=['SPR', 'SUM', 'FALL', 'HOL' ,'CHASE'] 
                                    
                                    # x = []

                                    for word in ocr_text_list:
                                        best_match = None
                                        best_ratio = 0
                                        
                                        for item in items:
                                            ratio = fuzz.ratio(word.lower(), item.lower())
                                            if ratio > 65 and ratio > best_ratio:
                                                best_match = item
                                                best_ratio = ratio
                                        
                                        if best_match:

                                            output_text.append("SEASON: {}".format(best_match))
                                            sesn=best_match

                                            # val=(best_match)
                                            # insert_in_db_details_season(conn,val)

                                        # else:
                                        #     output_text.append("SEASON: {}".format(word))
                                    
                                    year_list=['24', '25', '26']
                                    y = []
                                    for word in ocr_text_list:
                                        for year in year_list:                                   
                                            ratio = fuzz.ratio(word.lower(), year.lower())
                                            if ratio > 60:  # You can adjust this threshold as needed
                                                y.append(year)                                                                            
                                                output_text.append("{} : {}".format("SEASON_Year",y[0])) 
                                                
                                                yr=y[0]
                                                # insert_in_db_details_season_year(conn,val)                                       
                                                break        
                                else:
                                    
                                    ocr_text_list=[]
                                    for idx,text in enumerate(ocr_text):
                                        if idx!=0:
                                            ocr_text_list.append(text.description)

                                    Type_list=['NK','ER','BR','HAIR','RNG','BAG','SUN', 'KEY','OTR']
                                    t=[]

                                    for word in ocr_text_list:
                                        for types in Type_list:                                   
                                            ratio = fuzz.ratio(word.lower(), types.lower())
                                            if ratio > 60:  # You can adjust this threshold as needed
                                                t.append(types)
                                                category=t[0]
                                                print(t[0])  

                                                output_text.append("{} : {}".format("CATEGORY",category))                                        
                                                break 
                                        

                                    
                                    ocr_text_list=[]
                                    for idx,text in enumerate(ocr_text):
                                        if idx!=0:
                                            ocr_text_list.append(text.description)

                                    designer_list=['OS','MOS','DOS']
                                    des=[]

                                    for designer in list(set(ocr_text_list)):
                                        for design in designer_list:                                   
                                            ratio = fuzz.ratio(designer.lower() , design.lower())
                                            if ratio > 60:  # You can adjust this threshold as needed
                                                des.append(design)
                                                print(des[0])
                                                desi=des[0]                                                                            
                                                output_text.append("{} : {}".format("DESIGNER",desi))                                        
                                                break                
                                            
                            else:
                                " No Text Detected in Masked image ! "


                    filename=os.path.basename(image_path)
                    output_path=os.path.join(output_dir,f"{barcode_value}_FRONT_"+ filename )
                    cv2.imwrite(output_path,image) 

                

                    #     output_text.append("{} : {}".format("Length",length))    
                
                    #     output_text.append("{} : {}".format("Weight",weight))    
            
                    #     output_text.append("{} : {}".format("Date",date))    
                

                    values=(type,barcode_value,count)
                    
                    insert_in_db(conn,values)
                    type_value, bar_code, count_value = get_last_row_columns(conn)
                    val=(barcode_value,length,weight,sesn,yr,category,desi,date)
                    insert_in_db_details(conn,val)
            


            else:

                
                type="BACK"
               
                for box,cls,con in zip(boxes,classes,prob):
                        if model.names[int(cls)]!= 'jewelry':
                            return "","Empty Tag n no jewlery"

                        print("backkkkkkkk")
                        x1,y1,x2,y2=box
                        crop=image[int(y1):int(y2),int(x1):int(x2)]
                        masked_image=crop.copy()
                        barcode_value=scan(masked_image)
                        
                        if not barcode_value:
                            
                            for text in ocr_text:                
                            
                                    new_text=text.description.replace("BERNARDO","")
                                    new_text=new_text.replace("Bernardo","")
                                    new_text=new_text.replace("HandSample","")
                                    new_text=new_text.replace("In-HouseSample","")
                                    
                                    new_text=new_text.replace("Sample","")
                                    new_text=new_text.replace("Overseas","")
                                    new_text=new_text.replace("OverseasSample","")
                                    print(new_text)

                                    if len(new_text)>=6:

                                        x = re.findall("^\d{6,}$|^(?!(?:\d+|[A-Za-z]+)$)[A-Za-z0-9-]{1,}(?:[A-Za-z0-9-]{1,}){0,3}$", new_text)

                                    
                                        print(x)
                                        if x:
                                            new_barcode_value = x[0]
                                            barcode_found = False
                                            
                                            for i, entry in enumerate(output_text):
                                                if entry.startswith("Barcode :"):
                                                    old_value = entry.split(":")[1]
                                                    output_text[i] = "{} {}".format(entry, new_barcode_value)
                                                    barcode_found = True
                                                    barcode_value=old_value+new_barcode_value
                                                    break
                                            
                                            if not barcode_found:
                                                # output_text.append("Barcode : {}".format(new_barcode_value))
                                                barcode_value=new_barcode_value
                                

                            output_text.append("Barcode : {}".format(barcode_value))
                            filename=os.path.basename(image_path).split(".")[0]
                            cv2.imwrite(os.path.join(output_dir,f"{barcode_value}_CROP_{filename}.jpg"),crop)

                        
                        output_text.append("Barcode : {}".format(barcode_value))

                        




                        # ocr_text=detect_text(masked_image)
                        # for text in ocr_text:
                        #     new_text=text.description.replace("BERNARDO","")
                        #     new_text=new_text.replace("Bernardo","")
                        #     new_text=new_text.replace("HandSample","")
                        #     new_text=new_text.replace("In-HouseSample","")
                            
                        #     new_text=new_text.replace("Sample","")
                        #     new_text=new_text.replace("Overseas","")
                        #     new_text=new_text.replace("OverseasSample","")

                        #     print("lolololololo",new_text)
                        #     if len(new_text)>=6:
                        #         x = re.findall("^\d{6,}$|^(?!(?:\d+|[A-Za-z]+)$)[A-Za-z0-9-]{1,}(?:[A-Za-z0-9-]{1,}){0,3}$", new_text)
                        #         print("xxxxxxx",x)
                        #         if x:
                        #             print("TRUEEEE")
                        #             new_barcode_value = x[0]
                        #             barcode_found = False
                                    
                        #             for i, entry in enumerate(output_text):
                        #                 if entry.startswith("Barcode :"):
                        #                     old_value = entry.split(":")[1]
                        #                     print("oooooldddddddd",old_value)
                        #                     output_text[i] = "{} {}".format(entry, new_barcode_value)
                        #                     barcode_found = True
                        #                     barcode_value=old_value+new_barcode_value
                        #                     break
                                    
                        #             if not barcode_found:
                        #                 output_text.append("Barcode : {}".format(new_barcode_value))
                        #                 barcode_value=new_barcode_value

                                # if not len(x)==0:
                                #     output_text.append("{} : {}".format("Barcode",x[0]))
                                #     barcode_value =x[0]
                                #     # print(x[0]) 
                                # print(output_text)
                        
                
                
                print(output_text)
                type_value, bar_code, count_value = get_last_row_columns(conn)
                
            

            
                
                if type_value == "BACK"  and  barcode_value == bar_code :
                    # print(count_value)
                    count_value+=1
                    # print(count_value)
                    values=(type,barcode_value,count_value)

                    insert_in_db(conn,values)
                    # update_last_row_count(conn)
                    _,_,count_val=get_last_row_columns(conn)
                    
                    print("SAME Picture Uploaded ")
                    filename = os.path.basename(image_path)
                    output_path=os.path.join(output_dir,f"{barcode_value}_BACK-{count_val}_"+ filename )
                    cv2.imwrite(output_path,image)
            
                else:
                    # Reset the sequence number if the barcode is different
                    filename=os.path.basename(image_path)
                    output_path=os.path.join(output_dir,f"{barcode_value}_BACK_"+ filename )
                    cv2.imwrite(output_path,image)
                    # last_back_barcode = barcode_value
                    count=0
                    values=(type,barcode_value,count)

                    insert_in_db(conn,values)
                    get_last_row_columns(conn)




                val=(barcode_value,"NONE","NONE","NONE","NONE","NONE","NONE","NONE")
                insert_in_db_details(conn,val)
       

      
        print(output_text)
    

        
        filename=os.path.basename(image_path).split('.')[0]
        output_path=os.path.join(output_dir,filename)
        

        with open(f"{output_path}_output.txt",'w',encoding="utf-8") as file:
            for i in output_text:
                file.write(str(i) + '\n')


    return output_path,output_text


          

# Main function taking image path/folder and desired Output dir 
    
def main(image_path="Pending",output_dir = r"Pending_results",confidence=0.7,excel_file_name="output_data.xlsx"):

    conn=sqlite3.connect("Data.db")
    cursor=conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS details")

    cursor.execute('''CREATE TABLE IF NOT EXISTS info
                   (Type TEXT,Barcode TEXT,count INTEGER)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS details
                (Barcode TEXT,Length TEXT,Weight TEXT,Season TEXT,Season_Year,Category TEXT,Designer TEXT,Date TEXT)''')
    conn.commit()
    clear_database(conn)
    

    



    
    
    # make new dir every time if left empty
    if not output_dir:
        output_dir = os.path.join(".",uuid4().hex)

    # make output directory if not exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True) 

    # if it is file(image)
    if os.path.isfile(image_path):
        try:
            ot_path , ot_text = prediction(image_path,output_dir,confidence,conn)
        except Exception as e:
            ot_path,ot_text= "",str(e)    
    # if it is dir then iterate each folder and file
    elif os.path.isdir(image_path):
        for root,_,files in os.walk(image_path):
            for file in files:
                
                full_path=os.path.join(root,file)
                try:
                    ot_path , ot_text = prediction(full_path,output_dir,confidence,conn)   
                except Exception as e:
                    ot_path,ot_text="",str(e)
    else:
        print('Invalid file or Path !')  



    excel_file_name = 'output_data.xlsx'
    excel_file_path = os.path.join(output_dir, excel_file_name)
    write_db_to_csv(conn,excel_file_path)    

    conn.close()

    return ot_path , ot_text     

    



main()

# # if __name__ == "__main__":
# #     parser=argparse.ArgumentParser(description="Predction model")
# #     parser.add_argument('--image_path',"-i", type=str, help='Path to the image file or folder containing images', required=True)
# #     parser.add_argument('--output_dir',"-o", type=str, default='', help='Path to the output directory')
# #     parser.add_argument('--confidence',"-c", type=float, default=0.7, help='Confidence threshold for predictions')
# #     args = parser.parse_args()

# #     main(args.image_path, args.output_dir, args.confidence )


# conn=sqlite3.connect("test.db")
# cursor=conn.cursor()

# # cursor.execute('''INSERT TABLE IF NOT EXISTS info
# #                 (type TEXT,barcode TEXT)''')
# # conn.commit()
# # conn.close()
# query="Select * FROM info "
# # (type ,barcode )
# #             VALUES(?,?)'''
# # values=("FRONT","82762689293")
# # cursor=conn.cursor()
# cursor.execute(query)
# print(cursor.fetchall())
# conn.commit()
# conn.close()
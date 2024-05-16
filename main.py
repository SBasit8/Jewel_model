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


def get_last_row_columns(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM info ORDER BY rowid DESC LIMIT 1 OFFSET 1")
    row = cursor.fetchone()
    if row:
        # Assuming 0-indexed columns
        
        # Change the indices according to your table schema
        print("returnnn karega ")
        type_value = row[0]
        barcode_value = row[1]
        conn.commit()
        conn.close()
        return type_value, barcode_value
    return None, None



def insert_in_db(conn,values):

    cursor=conn.cursor()
    query='''INSERT INTO info (type ,barcode )
            VALUES(?,?)'''
    cursor.execute(query,values)
    

    print("Values inserted")
    get_query="SELECT * from info "
    cursor.execute(get_query)
    # items=
    print(cursor.fetchall())
    # for item in items:
    #     print(item)
    # cursor.close    
    conn.commit()
    
    return cursor.lastrowid,values[0],values[1]

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
        


#  results of predtiction and Bounding Boxes
count=0
last_back_barcode= None
def prediction(image_path,output_dir,confidence,conn):
    global last_back_barcode
    barcode_value=0
    filename,ext=os.path.splitext(image_path)
    if not (ext and (str(ext).lower() in [".png",".jpg",".jpeg"])):
        return
    image=cv2.imread(image_path)
    results = model.predict(image, conf=confidence)
    if results:
      boxes = results[0].boxes.xyxy.cpu().numpy()
      classes = results[0].boxes.cls.cpu()
      prob = results[0].boxes.conf.cpu()
      output_text= []
      
    
      x=len(boxes)
      if x>1:
            type="FRONT"
            last_back_barcode=None          
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
                                
                else:
                    masked_image=crop.copy()



                ocr_text=detect_text(masked_image)
            
                if model.names[int(cls)]== 'jewelry':
                   
                    
            
                    for text in ocr_text:                
                        # print('\n"{}"'.format(text.description))
                        # vertices = (['({},{})'.format(vertex.x, vertex.y)
                        #             for vertex in text.bounding_poly.vertices])
                                         
                        
                        # print('bounds: {}'.format(','.join(vertices)))
                        txt=text.description
                        txt=txt.replace(" ","")
                        
                        
                        # ^\d{6,}$|?
                        

                        if len(txt)>=7:

                            print("TEXT AFTERRRRRRRR",txt)
                            # print(txt)
                            pattern =r"^(?!(?:\d+|[A-Za-z]+)$)[A-Za-z0-9-]{1,}(?:[A-Za-z0-9-]{1,}){0,3}$"    
                                
                            x=match_regex(pattern,txt)        
                            # # # x = re.findall("^\d{6,}$|^(?!(?:\d+|[A-Za-z]+)$)[A-Za-z0-9-]{1,}(?:[A-Za-z0-9-]{1,}){0,3}$", txt)
                            # # regex= re.compile(r"^\d{6,}$|^(?!(?:\d+|[A-Za-z]+)$)[A-Za-z0-9-]{1,}(?:[A-Za-z0-9-]{1,}){0,3}$")
                            # srch =regex.search(txt)
                            print("RE SEARCH KRKE DIA HOGA")
                            print(x)

                            



                            

                            if not len(x)==0:
                                output_text.append("{} : {}".format("Barcode",x[0]))
                                barcode_value =x[0]
                                print(x[0]) 
                            print(output_text)
                    filename=os.path.basename(image_path).split(".")[0]
                    cv2.imwrite(os.path.join(output_dir,f"{barcode_value}_CROP_{filename}.jpg"),crop)
                            
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
                                    ratio = fuzz.ratio(word.lower(), type.lower())
                                    if ratio > 60:  # You can adjust this threshold as needed
                                        t.append(types)                                                                            
                                        output_text.append("{} : {}".format("CATEGORY",t[0]))                                        
                                        break        
                                      
                    else:
                        " No Text Detected in Masked image ! "


            filename=os.path.basename(image_path)
            output_path=os.path.join(output_dir,f"{barcode_value}_FRONT_"+ filename )
            cv2.imwrite(output_path,image) 


            output_text.append("{} : {}".format("Length",length))    
            output_text.append("{} : {}".format("Weight",weight))   
            output_text.append("{} : {}".format("DATE",date)) 

            values=(type,barcode_value)
            
            insert_in_db(conn,values)
            print("FUNCIONNN RETURN VALUESSSS")
            


      else:
        
        type="BACK"
        for box,cls,con in zip(boxes,classes,prob):
                x1,y1,x2,y2=box
                
                crop=image[int(y1):int(y2),int(x1):int(x2)]
                masked_image=crop.copy()

                ocr_text=detect_text(masked_image)
                for text in ocr_text:
                    # print('\n"{}"'.format(text.description))
                    # vertices = (['({},{})'.format(vertex.x, vertex.y)
                    #             for vertex in text.bounding_poly.vertices])

                    # print('bounds: {}'.format(','.join(vertices)))
                    if len(text.description)>=10:
                        x = re.findall("^\d{6,}$", text.description)

                        if not len(x)==0:
                            output_text.append("{} : {}".format("Barcode",x[0]))
                            barcode_value =x[0]
                            print(x[0]) 
                        print(output_text)
        
        values=(type,barcode_value)
        insert_in_db(conn,values)
        type_value, bar_code = get_last_row_columns(conn)
        
        print("FUNCIONNN RETURN VALUESSSS")
       

        print(type_value)
        print(bar_code)

        
        if type_value == "BACK"  and  barcode_value == bar_code :
            count=+1
            print("SAME picture uploaded ")
            filename = os.path.basename(image_path)
            output_path=os.path.join(output_dir,f"{barcode_value}_BACK-{count}_"+ filename )
            cv2.imwrite(output_path,image)
        # filename = os.path.basename(image_path)
        # filename_parts = filename.split("_")
        # if len(filename_parts) == 3 and filename_parts[-2] == "BACK":
        #     # Increment the sequence number
        #     sequence_number = int(filename_parts[-1].split(".")[0]) + 1
        #     new_filename = f"BACK_{sequence_number}.jpg"
        #     output_path = os.path.join(output_dir, new_filename)
        #     os.rename(os.path.join(output_dir, filename), output_path)
        #     cv2.imwrite(output_path,image)
        else:
            # Reset the sequence number if the barcode is different
            filename=os.path.basename(image_path)
            output_path=os.path.join(output_dir,f"{barcode_value}_BACK_"+ filename )
            cv2.imwrite(output_path,image)
            last_back_barcode = barcode_value
            count=0

        # values=(type,barcode_value)
        # insert_in_db(conn,values)
        
       
        # last_row_id,TP,bar=

        
        
        
        # filename=os.path.basename(image_path)
        # output_path=os.path.join(output_dir,f"{barcode_value}_BACK_"+ filename )
        # cv2.imwrite(output_path,image)

        # type_value, bar_code = get_last_row_columns(conn)

        # if type_value == "BACK"  and  barcode_value == bar_code :
        #     count=+1
        #     print("SAME picture uploaded ")
        #     filename = os.path.basename(image_path)
        #     output_path=os.path.join(output_dir,f"{barcode_value}_BACK_{count}"+ filename )
        #     cv2.imwrite(output_path,image)
            
        # else:
        #     filename = os.path.basename(image_path)
        #     output_path=os.path.join(output_dir,f"{barcode_value}_BACK_"+ filename)
        #     cv2.imwrite(output_path,image)
        #     count=0
            


       

        
        # filename=os.path.basename(image_path)
        # output_path=os.path.join(output_dir,f"{barcode_value}_BACK_"+ filename )
        # cv2.imwrite(output_path,image)
      
      print(output_text)

           
      filename=os.path.basename(image_path).split('.')[0]
      output_path=os.path.join(output_dir,filename)
      

      with open(f"{output_path}_output.txt",'w',encoding="utf-8") as file:
          for i in output_text:
            file.write(str(i) + '\n')
          

# Main function taking image path/folder and desired Output dir 
    
def main(image_path=r"Input_images\88.jpg",output_dir = r"output_results",confidence=0.7):

    conn=sqlite3.connect("Data.db")
    cursor=conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS info
                   (type TEXT,barcode TEXT)''')
    conn.commit()
    

    



    
    
    # make new dir every time if left empty
    if not output_dir:
        output_dir = os.path.join(".",uuid4().hex)

    # make output directory if not exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True) 

    # if it is file(image)
    if os.path.isfile(image_path):
        prediction(image_path,output_dir,confidence,conn)
    # if it is dir then iterate each folder and file
    elif os.path.isdir(image_path):
        for root,_,files in os.walk(image_path):
            for file in files:
                
                full_path=os.path.join(root,file)
                prediction(full_path,output_dir,confidence,conn)   

    else:
        print('Invalid file or Path !')    

    



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
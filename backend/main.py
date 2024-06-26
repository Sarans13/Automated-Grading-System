from fastapi.middleware.cors import CORSMiddleware
from typing import Union
from fastapi import File, UploadFile, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys
from PIL import Image
from pathlib import Path

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)
from recognition.certificate_generator import update_marks_sheet, make_certificate
from recognition.barcode_reader import barcode_reader
from recognition.prediction import get_prediction


app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
os.chdir(r"answersheets/")


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    print(file)
    file_name = file.filename

    try:
        contents = file.file.read()
        print(os.getcwd())
        with open(file_name, 'wb') as f:  # type: ignore
            f.write(contents)
    except Exception as e:
        print(e)
        return {"message": "There was an error uploading the file"}
    finally:
        file.file.close()

    crop_marks(file_name)
    crop_barcode(file_name)

    info = barcode_reader(
        image_path=fr'../answersheets/{add_file_name(file_name, "_cropped_barcode")}')
    print(info)
    mark = get_prediction(
        image_path=fr'../answersheets/{add_file_name(file_name, "_cropped_marks")}')
    print(mark)

    student_id, subject_code = info.split(",")
    update_marks(student_id, subject_code, mark)

    return {"marks": mark, "student_id":student_id, "subject_code":subject_code}

class Student(BaseModel):
    student_id: str

@app.post("/send_pdf")
async def send_pdf(student: Student):
    print(student.student_id)
    print(type(student.student_id))

    make_certificate(student.student_id)

    certificate_path = Path(f'../certificates/Certificate-{student.student_id}.pdf')
    if not certificate_path.is_file():
        raise HTTPException(status_code=404, detail="Certificate not found")


    response = FileResponse(str(certificate_path))
    response.headers["Content-Disposition"] = f"attachment; filename=Certificate-{student.student_id}.pdf"
    return response

def crop_marks(image_path):
    original_image = Image.open(image_path)
    cropped_image = original_image.crop((489, 200, 489+66, 200+50))
    cropped_image.save(f'{add_file_name(image_path, "_cropped_marks")}')


def crop_barcode(image_path):
    original_image = Image.open(image_path)
    cropped_image = original_image.crop((98-10, 22-10, 98+400+10, 22+76+10))
    cropped_image.save(f'{add_file_name(image_path, "_cropped_barcode")}')


def add_file_name(file_path, attribute):
    file_name, file_extension = os.path.splitext(file_path)

    return file_name + attribute + file_extension


def update_marks(student_id, subject_code, mark):
    update_marks_sheet(student_id=student_id, subject_code=subject_code, endsem_marks=mark)


# print(add_file_name('answersheets/answer.sheet1.jpg', "_cropped_marks"))
# crop_barcode(r'../answersheets/answersheet2.jpg')
# print(barcode_reader(r'../answersheets/answersheet2_cropped_barcode.jpg'))

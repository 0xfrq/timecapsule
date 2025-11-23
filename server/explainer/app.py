import time
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()  
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_video(video_path):
    print(f"Uploading {video_path}")
    video_file = genai.upload_file(path=video_path)
    print(f"Completed upload: {video_file.uri}")

    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError(f"Video processing failed: {video_file.state.name}")

    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    #layering
    #prompt = "Describe exactly what happens in this video, dan dari deskripsi yang anda dapatkan generate comment organik sosial media tiktok dari deskripsi video ini, gunakan slang slang bahasa indonesia yang sering digunakan dan terlihat organik. buat komentar dalam kurang dari 1 kalimat, gunakan bahasa edgy jaksel juga bisa atau menggunakan brainrot juga boleh lebih edgy dan lebih brainrot lebih baik, generate 20 comment, buat dalam bentuk json beserta username dan isi comment nya. untuk usernamenya, username dengan nama orang pada umumnya saja"
   
   # yg ini ngga
    prompt = "generate comment organik sosial media tiktok berbasis video yang anda lihat, gunakan slang slang bahasa indonesia yang sering digunakan dan terlihat organik. buat komentar dalam kurang dari 1 kalimat, gunakan bahasa edgy jaksel juga bisa atau menggunakan brainrot juga boleh lebih edgy dan lebih brainrot lebih baik, generate 20 comment, buat dalam bentuk json beserta username dan isi comment nya. untuk usernamenya, username dengan nama orang pada umumnya saja"

    response = model.generate_content(
        [video_file, prompt],
        request_options={"timeout": 600}
    )

    print(response.text)

    genai.delete_file(video_file.name)

if __name__ == "__main__":
    analyze_video("prometheus.mp4")

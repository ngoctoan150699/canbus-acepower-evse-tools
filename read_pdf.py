import PyPDF2

try:
    with open('d:/DuAn/1.EVSE/power_module_/USB-CAN-B - Waveshare Wiki.pdf', 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for i, page in enumerate(reader.pages):
            text += f"\n--- Page {i+1} ---\n"
            text += page.extract_text()
        pass
        
        with open('d:/DuAn/1.EVSE/power_module_/waveshare_can_b.txt', 'w', encoding='utf-8') as out:
            out.write(text)
        print("\n\nFull text saved to waveshare_can_b.txt")
except Exception as e:
    print("Error reading PDF:", e)

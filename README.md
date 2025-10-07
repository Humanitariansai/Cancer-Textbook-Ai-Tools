# Cancer-Textbook-Ai-Tools
# Cancer-Textbook-Image-Search  
Author: Humanitarians.AI Team  
Collaborator: Kalyan Kumar Chenchu Malakondaiah  

An AI-powered pipeline to preprocess textbook chapters, generate search queries, retrieve medical images from NIH Visuals Online, and download them in full resolution for integration into the Cancer Textbook project.  

---

## Project Overview  
This project builds a modular system that:  

- Preprocesses textbook chapters into structured datasets  
- Generates search queries based on selected chapter text  
- Automates NIH Visuals Online search using Selenium  
- Extracts metadata and image links via BeautifulSoup  
- Downloads both thumbnails and high-resolution images  
- Saves results with CSV manifests for easy integration  

---

## Project Structure  

src/
├── data_preprocessing.py # Prepares dataset from raw chapter files
├── query_builder.py # Builds search query text from a selected chapter
├── image_search.py # Uses Selenium + BeautifulSoup to scrape NIH Visuals
├── nih_scraper.py # Core scraper logic for NIH
├── image_downloader.py # Downloads images (thumbnails + full-resolution)

data/
├── chapters/ # Raw chapter markdown/text files
├── chapters_dataset.csv # Preprocessed dataset (chapter → paragraphs)
├── query_text.txt # Query text for image search
├── nih_results.csv # Search results from NIH
└── nih_images/ # Downloaded images + manifest


---

## Key Features  
- **Text Preprocessing**: Converts chapters into structured CSVs (chapter, paragraph, text)  
- **Automated Query Building**: Extracts keywords for NIH searches  
- **Web Scraping with Selenium**: Captures dynamically rendered results from NIH Visuals  
- **Metadata Export**: Titles, URLs, thumbnails saved in CSV format  
- **Full-Resolution Downloads**: Retrieves high-quality medical images where available  
- **Manifest Tracking**: Generates CSV logs for reproducibility and dataset management  

---

## Getting Started  
1. Clone the repository  
   ```bash
   git clone https://github.com/Humanitariansai/Cancer-Textbook-Ai-Tools.git
   cd Cancer-Textbook-Ai-Tools

2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows

3. Install dependencies
pip install -r requirements.txt

4. Run preprocessing
python src/data_preprocessing.py

5. Build queries
python src/query_builder.py --chapter 31

6. Search NIH for images
python src/image_search.py

7. Download images
python src/image_downloader.py

Technologies Used

Python: Core pipeline

Selenium + ChromeDriver: Automated web scraping

BeautifulSoup4: HTML parsing

Pandas: Data preprocessing and CSV management

Sentence-Transformers: Query embeddings (planned for expansion)

Pillow (PIL): Image processing

Contributors

Humanitarians.AI Team

Kalyan Kumar Chenchu Malakondaiah
Akshit Saxena



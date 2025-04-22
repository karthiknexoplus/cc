# Parking Management Command Center

A modern web-based command center for handheld-based parking management system, powered by RoyalUniversys.com.

## Features

- Modern split-screen login/signup interface
- Responsive design
- Secure user authentication
- Clean and intuitive UI

## Setup Instructions

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a parking image:
- Place a parking-related image in `static/images/parking.jpg`
- The image should be high-quality and relevant to parking management

4. Run the application:
```bash
python app.py
```

5. Access the application:
- Open your browser and go to `http://localhost:5000`

## Project Structure

```
.
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css  # Stylesheet
│   └── images/
│       └── parking.jpg # Parking system image
└── templates/
    └── index.html     # Main template
```

## Notes

- This is a basic implementation with in-memory user storage
- For production use, you should:
  - Implement a proper database
  - Add more security features
  - Use environment variables for sensitive data
  - Add proper error handling
  - Implement password reset functionality

## Powered by

RoyalUniversys.com 
# Scramble PDF Text Encodings

<p align="center">
  <img src="./img/logo.png" alt="描述文字" width="25%" />
</p>

Make your essay unreadable to simple programs. Still readable by humans and OCR.

If you think this is a terrible idea, I knew it is, and it's probably not for you.

## Usage Guide

### Install

#### Install Poetry

```shell
curl -sSL https://install.python-poetry.org | python3 -
# or follow the instructions on Poetry’s official site.
```

#### Clone the Repository

```shell
git clone https://github.com/VermiIIi0n/scramble-pdf.git
cd scramble-pdf
```

#### Install Dependencies

```shell
poetry install
```

#### Activate the Virtual Environment

```shell
poetry env activate
# poetry shell
```

### Run in CLI

```shell
python -m scramblepdf input_pdf output_pdf --ratio 0.3
# choose ratio between 0 and 1.0, default: 1.0
```

### Run in WebGUI

```shell
streamlit run gui/web/app.py
```

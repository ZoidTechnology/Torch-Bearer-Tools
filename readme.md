# Torch Bearer Tools

A collection of tools and examples to extend the capabilities of spectrometers manufactured by [Torch Bearer](https://www.torchbearer.tech/).

## App Patcher

A tool for modifying the official [Flameeye Android app](https://play.google.com/store/apps/details?id=tech.torchbearer.flameeye) to unlock additional features and improve functionality.

### Requirements

- [Node.js 22](https://nodejs.org/en/download)
- [Java 8](https://www.java.com/en/download/)

### Usage

- Download Flameeye version 1.6.4 to the app-patcher directory and rename it `flameeye.apk`.
- Enter the app-patcher directory and use `npm install` to install dependencies.
- Use `npm run assemble` to assemble and sign a patched app.
- Use `npm run create-patches` to create patches from modified files.

## Interface

A Python implementation of the serial protocol used by Torch Bearer's basic spectrometers, including decoding the obfuscated spectral data.

### Requirements

- [Python 3.10](https://www.python.org/downloads/)

### Usage

- Use `pip install colour-science matplotlib pyserial` to install dependencies.
- Enter the interface directory and use `python main.py <port>` to display a spectral power distribution plot.

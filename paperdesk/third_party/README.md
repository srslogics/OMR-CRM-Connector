# Local recognizer attribution

PaperDesk uses the English PP-OCRv5 mobile recognition model developed in [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) and distributed in ONNX format by [RapidAI/RapidOCR](https://github.com/RapidAI/RapidOCR). The repositories publish Apache-2.0 licenses; copies are included here. Copyright (c) 2021 RapidOCR Authors / RapidAI. Model weights are downloaded unchanged and are not committed to this repository.

Pinned model: `en_PP-OCRv5_rec_mobile.onnx`, RapidAI model distribution revision `v3.9.2`.

Source: <https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/onnx/PP-OCRv5/rec/en_PP-OCRv5_rec_mobile.onnx>

SHA-256: `c3461add59bb4323ecba96a492ab75e06dda42467c9e3d0c18db5d1d21924be8`.

`setup_ocr.py` checks the digest before installation. ONNX Runtime executes the model on the local CPU; student images are never sent to the model download host.

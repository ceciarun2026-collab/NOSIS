from pdf_reader import build_document

from extractor import extract_information

from prompt_builder import build_prompt


def process_document(pdf):

    documento = build_document(pdf)

    criterios = build_prompt()

    respuesta = extract_information(

        documento["texto_completo"],

        criterios

    )

    return respuesta
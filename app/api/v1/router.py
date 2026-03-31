from fastapi import APIRouter
from app.api.v1 import questions, quiz, progress, parse, generate, import_, export, question_sets

router = APIRouter()
router.include_router(questions.router, prefix="/questions", tags=["questions"])
router.include_router(question_sets.router, prefix="/question-sets", tags=["question-sets"])
router.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
router.include_router(progress.router, prefix="/progress", tags=["progress"])
router.include_router(parse.router, prefix="/parse", tags=["parse"])
router.include_router(generate.router, prefix="/generate", tags=["generate"])
router.include_router(import_.router, prefix="/import", tags=["import"])
router.include_router(export.router, prefix="/export", tags=["export"])

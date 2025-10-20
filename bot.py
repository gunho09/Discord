import discord
from discord.ext import commands
import os
import google.generativeai as genai
import asyncio

# 환경 변수에서 디스코드 봇 토큰 로드
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 제미나이 클라이언트 초기화
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.")
    exit()

# 봇의 권한 설정 (Intents)
intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용을 읽기 위한 권한

# 봇 클라이언트 생성
bot = commands.Bot(command_prefix="!", intents=intents)

# 공통 시스템 프롬프트
SYSTEM_INSTRUCTION = "You are a world-class AI assistant specialized in all aspects of programming. Your goal is to provide expert-level help to developers. You can write code, debug issues, explain complex software engineering concepts, and provide guidance on best practices. Please provide answers in Korean."

# 제미나이 모델 설정 (두 가지 모델)
flash_model = genai.GenerativeModel(
    model_name="models/gemini-flash-latest",
    system_instruction=SYSTEM_INSTRUCTION,
)
pro_model = genai.GenerativeModel(
    model_name="models/gemini-2.5-pro",
    system_instruction=SYSTEM_INSTRUCTION,
)

# 사용자별 대화 기록을 저장할 딕셔너리 (두 가지 모드)
flash_conversations = {}
pro_conversations = {}

# 봇이 준비되었을 때 실행될 이벤트
@bot.event
async def on_ready():
    print(f'{bot.user.name}이(가) 성공적으로 로그인했습니다!')

# 제미나이 응답 생성을 위한 공통 헬퍼 함수
async def generate_gemini_response(ctx, question, model, conversations):
    response_message = await ctx.send(f"'{question}'에 대해 생각 중입니다... 🤔")
    
    try:
        user_id = ctx.author.id
        if user_id not in conversations:
            conversations[user_id] = model.start_chat(history=[])
        
        chat_session = conversations[user_id]

        response = await chat_session.send_message_async(question, stream=True)
        
        accumulated_content = ""
        last_update_time = asyncio.get_event_loop().time()
        
        async for chunk in response:
            try:
                if chunk.text:
                    accumulated_content += chunk.text
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_update_time > 1.5:
                        if accumulated_content.strip() and len(accumulated_content) < 2000:
                            await response_message.edit(content=accumulated_content)
                            last_update_time = current_time
            except Exception:
                pass  # 빈 청크 등 문제 있는 부분 무시

        if len(accumulated_content) <= 2000:
            if accumulated_content.strip():
                await response_message.edit(content=accumulated_content)
            else:
                await response_message.edit(content="죄송합니다, 답변을 생성하지 못했습니다.")
        else:
            await response_message.delete()
            parts = [accumulated_content[i:i+1990] for i in range(0, len(accumulated_content), 1990)]
            for part in parts:
                if part.strip():
                    await ctx.send(part)

    except Exception as e:
        await response_message.edit(content=f"오류가 발생했습니다: {e}")

# '!질문' 명령어 (빠른 Flash 모델 사용)
@bot.command(name='질문')
async def ask_flash(ctx, *, question: str):
    """빠른 답변 (Flash 모델)을 요청합니다."""
    await generate_gemini_response(ctx, question, flash_model, flash_conversations)

# '!심층리서치' 명령어 (고성능 Pro 모델 사용)
@bot.command(name='심층리서치')
async def ask_pro(ctx, *, question: str):
    """깊이 있는 답변 (Pro 모델)을 요청합니다."""
    await generate_gemini_response(ctx, question, pro_model, pro_conversations)

# 봇 실행
if DISCORD_BOT_TOKEN:
    bot.run(DISCORD_BOT_TOKEN)
else:
    print("디스코드 봇 토큰(DISCORD_BOT_TOKEN)이 환경 변수에 설정되지 않았습니다.")

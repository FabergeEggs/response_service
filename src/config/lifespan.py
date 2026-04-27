from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio
from src.usecases.kafka_consumer import KafkaConsumerService
from src.usecases.kafka_producer import kafka_producer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    consumer_service = KafkaConsumerService()
    await consumer_service.start()
    app.state.kafka_consumer = consumer_service
    
    await kafka_producer.start()
    
    asyncio.create_task(consumer_service.consume_messages())
    
    yield
    
    # Shutdown
    await consumer_service.stop()
    await kafka_producer.stop()
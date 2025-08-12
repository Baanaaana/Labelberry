import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function clearDatabase() {
  console.log('Clearing all data from database...')
  
  try {
    // Delete in correct order to respect foreign key constraints
    await prisma.errorLog.deleteMany()
    console.log('✓ Cleared error logs')
    
    await prisma.metric.deleteMany()
    console.log('✓ Cleared metrics')
    
    await prisma.printJob.deleteMany()
    console.log('✓ Cleared print jobs')
    
    await prisma.configuration.deleteMany()
    console.log('✓ Cleared configurations')
    
    await prisma.pi.deleteMany()
    console.log('✓ Cleared printers')
    
    await prisma.apiKey.deleteMany()
    console.log('✓ Cleared API keys')
    
    await prisma.labelSize.deleteMany()
    console.log('✓ Cleared label sizes')
    
    await prisma.systemSetting.deleteMany()
    console.log('✓ Cleared system settings')
    
    await prisma.user.deleteMany()
    console.log('✓ Cleared users')
    
    console.log('\nDatabase cleared successfully!')
  } catch (error) {
    console.error('Error clearing database:', error)
  } finally {
    await prisma.$disconnect()
  }
}

clearDatabase()
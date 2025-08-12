import { PrismaClient } from '@prisma/client'
import { hash } from 'bcryptjs'

const prisma = new PrismaClient()

async function main() {
  // Create default admin user
  const adminPassword = await hash('admin123', 12)
  const adminUser = await prisma.user.upsert({
    where: { username: 'admin' },
    update: {},
    create: {
      username: 'admin',
      password: adminPassword,
      role: 'admin'
    }
  })
  console.log('Created admin user:', adminUser)

  // Create default label sizes
  const labelSizes = [
    { name: '4x6 inches', width: 4, height: 6, unit: 'inch' },
    { name: '4x4 inches', width: 4, height: 4, unit: 'inch' },
    { name: '2x1 inches', width: 2, height: 1, unit: 'inch' },
    { name: '100x150 mm', width: 100, height: 150, unit: 'mm' },
    { name: '100x100 mm', width: 100, height: 100, unit: 'mm' },
  ]

  for (const size of labelSizes) {
    await prisma.labelSize.upsert({
      where: { name: size.name },
      update: {},
      create: size
    })
  }
  console.log('Created label sizes')

  // No sample data - keep database clean for production use
  console.log('Database initialized with admin user and label sizes only')

  console.log('Database seeded successfully!')
}

main()
  .then(async () => {
    await prisma.$disconnect()
  })
  .catch(async (e) => {
    console.error(e)
    await prisma.$disconnect()
    process.exit(1)
  })
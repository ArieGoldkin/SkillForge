---
description: TypeScript type safety validation
---
Run comprehensive type checking:

Backend:
```bash
cd backend && poetry run ty check app/ --exclude "app/evaluation/*"
```

Frontend:
```bash
cd frontend && npm run typecheck
```

Follow SkillForge type-safety-validation patterns:
- Zod runtime validation
- tRPC type-safe APIs
- Prisma type-safe ORM
- Full type coverage from DB to UI

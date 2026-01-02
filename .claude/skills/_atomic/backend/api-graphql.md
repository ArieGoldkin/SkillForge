---
name: api-graphql
description: GraphQL schema design patterns
version: 1.0.0
tags: [api, graphql, schema, mutations]
size: atomic
domain: backend
---

# GraphQL API Design

## Schema Principles

### Nullable by Default

```graphql
type User {
  id: ID!              # Non-null (required)
  email: String!       # Non-null
  name: String         # Nullable (optional)
  avatar: String       # Nullable
}
```

### Connections for Lists

```graphql
type Query {
  users(first: Int, after: String): UserConnection!
}

type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type UserEdge {
  node: User!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

### Input Types for Mutations

```graphql
input CreateUserInput {
  email: String!
  name: String!
  role: UserRole!
}

type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
}

type CreateUserPayload {
  user: User
  errors: [UserError!]
}

type UserError {
  field: String!
  message: String!
  code: String!
}
```

## Query Examples

```graphql
# Single resource
query GetUser {
  user(id: "123") {
    id
    name
    posts { id, title }
  }
}

# List with filters
query GetUsers {
  users(
    first: 10
    after: "cursor123"
    filter: { role: DEVELOPER, status: ACTIVE }
  ) {
    edges {
      node { id, name, email }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

## Error Handling

```json
{
  "data": {
    "createUser": {
      "user": null,
      "errors": [
        {
          "field": "email",
          "message": "Email already taken",
          "code": "DUPLICATE_EMAIL"
        }
      ]
    }
  }
}
```

## Best Practices

- **Nullable by default** - Only use `!` for truly required fields
- **Use Connections** - Relay-style pagination for lists
- **Input types** - Group mutation arguments
- **Payload types** - Return both data and errors

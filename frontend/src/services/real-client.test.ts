import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockData = vi.hoisted(() => {
  type RequestInterceptor = (config: Record<string, unknown>) => Record<string, unknown>
  type ResponseFulfilled = (res: unknown) => unknown
  type ResponseErrorHandler = (error: { response: { status: number; data: Record<string, unknown> } }) => Promise<never>

  const requestHandlers: { fulfilled: RequestInterceptor[]; rejected: ((error: unknown) => unknown)[] } = { fulfilled: [], rejected: [] }
  const responseHandlers: { fulfilled: ResponseFulfilled[]; rejected: ResponseErrorHandler[] } = { fulfilled: [], rejected: [] }

  const instance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn((fulfilled: RequestInterceptor, rejected: (error: unknown) => unknown) => {
          requestHandlers.fulfilled.push(fulfilled)
          if (rejected) requestHandlers.rejected.push(rejected)
        }),
      },
      response: {
        use: vi.fn((fulfilled: ResponseFulfilled, rejected: ResponseErrorHandler) => {
          responseHandlers.fulfilled.push(fulfilled)
          if (rejected) responseHandlers.rejected.push(rejected)
        }),
      },
    },
  }

  return { instance, requestHandlers, responseHandlers }
})

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockData.instance),
  },
}))

import { RealClient } from './real-client'

describe('RealClient', () => {
  let client: RealClient

  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    client = new RealClient()
  })

  describe('auth methods', () => {
    it('login posts to /auth/login with email and password', async () => {
      mockData.instance.post.mockResolvedValue({
        data: { access_token: 'jwt', token_type: 'bearer', expires_in_days: 7 },
      })

      const result = await client.login('a@b.com', 'secret')

      expect(mockData.instance.post).toHaveBeenCalledWith('/auth/login', {
        email: 'a@b.com',
        password: 'secret',
      })
      expect(result.access_token).toBe('jwt')
    })

    it('register posts to /auth/register with email, password, and display_name', async () => {
      mockData.instance.post.mockResolvedValue({
        data: { access_token: 'jwt', token_type: 'bearer', expires_in_days: 7 },
      })

      const result = await client.register('a@b.com', 'secret', 'Alice')

      expect(mockData.instance.post).toHaveBeenCalledWith('/auth/register', {
        email: 'a@b.com',
        password: 'secret',
        display_name: 'Alice',
      })
      expect(result.access_token).toBe('jwt')
    })

    it('register omits display_name when not provided', async () => {
      mockData.instance.post.mockResolvedValue({
        data: { access_token: 'jwt', token_type: 'bearer', expires_in_days: 7 },
      })

      await client.register('a@b.com', 'secret')

      expect(mockData.instance.post).toHaveBeenCalledWith('/auth/register', {
        email: 'a@b.com',
        password: 'secret',
        display_name: undefined,
      })
    })

    it('getMe gets /auth/me and returns user profile', async () => {
      const userProfile = {
        id: '1',
        email: 'a@b.com',
        display_name: 'Alice',
        has_first_agent: false,
        created_at: '2024-01-01T00:00:00Z',
      }
      mockData.instance.get.mockResolvedValue({ data: userProfile })

      const result = await client.getMe()

      expect(mockData.instance.get).toHaveBeenCalledWith('/auth/me')
      expect(result).toEqual(userProfile)
    })
  })

  describe('request interceptor', () => {
    it('injects auth token from localStorage into request headers', () => {
      window.localStorage.setItem('auth_token', 'test-jwt')

      const handler = mockData.requestHandlers.fulfilled[0]
      const config = { headers: {} as Record<string, string> }
      handler(config)

      expect(config.headers).toEqual({ Authorization: 'Bearer test-jwt' })
    })

    it('does not inject auth header when no token exists', () => {
      const handler = mockData.requestHandlers.fulfilled[0]
      const config = { headers: {} as Record<string, string> }
      handler(config)

      expect(config.headers).toEqual({})
    })
  })

  describe('response interceptor', () => {
    it('removes token on 401', async () => {
      window.localStorage.setItem('auth_token', 'stale-jwt')
      const error = { response: { status: 401, data: { detail: 'Unauthorized' } } }
      const handler = mockData.responseHandlers.rejected[0]

      expect(window.localStorage.getItem('auth_token')).toBe('stale-jwt')

      await expect(handler(error)).rejects.toThrow()

      expect(window.localStorage.getItem('auth_token')).toBeNull()
    })

    it('passes through non-401 errors', async () => {
      const error = { response: { status: 500, data: { detail: 'Server error' } } }
      const handler = mockData.responseHandlers.rejected[0]

      await expect(handler(error)).rejects.toThrow()
    })
  })
})

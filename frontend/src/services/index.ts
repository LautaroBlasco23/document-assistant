import { RealClient } from './real-client'
import { MockClient } from './mock-client'
import type { ServiceClient } from './client.interface'

export const client: ServiceClient =
  import.meta.env.VITE_MOCK === 'true' ? new MockClient() : new RealClient()

export type { ServiceClient } from './client.interface'

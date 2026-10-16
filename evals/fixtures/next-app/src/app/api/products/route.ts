import { listProducts } from '@/server/products';

export async function GET() {
  return Response.json(await listProducts());
}

import { listProducts } from '@/server/products';
import { ProductFilters } from './_components/ProductFilters';

export default async function ProductsPage() {
  const products = await listProducts();
  return (<main><ProductFilters /><ul>{products.map((p) => <li key={p.id}>{p.name}</li>)}</ul></main>);
}

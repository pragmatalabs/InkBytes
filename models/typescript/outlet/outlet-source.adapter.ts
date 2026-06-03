import { OutletSource } from './outlet-source';

export class OutletSourceAdapter {
  adapt(item: OutletSource): OutletSource {
    const attributes = item.attributes;
    // You can add any transformation or default value setting logic here
    return new OutletSource(item.id, attributes);
  }
}

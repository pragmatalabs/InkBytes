
import { OutletAttributes } from './outlet-attributes';

export class OutletSource {
  constructor(
    public id: number,
    public attributes: OutletAttributes,

  ) {
    this.attributes.tags = [];
  }
}

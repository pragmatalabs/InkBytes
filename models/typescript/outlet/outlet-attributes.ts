export class OutletAttributes {

  constructor(
    public name: string,
    public url: string,
    public createdAt: Date,
    public updatedAt: Date,
    public publishedAt: Date,
    public active: boolean | null,
    public tags : any[],
    public avatars : any[],
  ) {}
}


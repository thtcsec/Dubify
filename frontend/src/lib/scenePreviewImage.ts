/** Preview backgrounds: Wikipedia thumb for hook scene only (export uses Pexels/Commons). */

export function scenePreviewImageUrl(
  _topic: string,
  _sceneTitle: string,
  sceneIndex: number,
  wikiThumbnailUrl?: string,
): string {
  if (sceneIndex === 0 && wikiThumbnailUrl?.trim()) {
    return wikiThumbnailUrl.trim();
  }
  return '';
}

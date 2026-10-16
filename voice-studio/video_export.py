"""Aspect-ratio preserving export sizes, bounded by UHD 4K."""
RESOLUTIONS = {'original': None, '720p': (1280,720), '1080p': (1920,1080), '2160p': (3840,2160)}


def output_size(width,height,resolution='original'):
    if resolution not in RESOLUTIONS or min(width,height)<2:
        raise ValueError('Độ phân giải xuất không hợp lệ.')
    bounds=RESOLUTIONS[resolution] or (3840,2160)
    if height>width:
        bounds=bounds[::-1]
    factor=min(bounds[0]/width,bounds[1]/height)
    if resolution=='original':
        factor=min(1,factor)
    return max(2,int(width*factor)//2*2),max(2,int(height*factor)//2*2)


def scale_filter(meta,resolution):
    size=output_size(meta['width'],meta['height'],resolution)
    return (f'scale={size[0]}:{size[1]}:flags=lanczos,setsar=1' if size!=(meta['width'],meta['height']) else None),size

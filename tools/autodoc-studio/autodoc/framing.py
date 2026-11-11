"""Output geometry uses the selected short edge for both orientations."""
def dimensions(short_edge,aspect_ratio='16:9'):
    short_edge=int(short_edge)
    if short_edge not in [360,720,1080]:raise ValueError('Độ nét phải là 720 hoặc 1080; preview dùng 360.')
    if aspect_ratio not in ['16:9','9:16']:raise ValueError('Tỷ lệ cần là 16:9 ngang hoặc 9:16 dọc.')
    long_edge=round(short_edge*16/9)//2*2
    return (long_edge,short_edge) if aspect_ratio=='16:9' else (short_edge,long_edge)

def pointer_in_image(x,y,box):
    if not box:return None
    left,top,width,height=box
    if width<=0 or height<=0 or not left<=x<=left+width or not top<=y<=top+height:return None
    return ((x-left)/width,(y-top)/height)

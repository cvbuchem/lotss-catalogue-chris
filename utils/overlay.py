# overlay code ripped out of show_overlay's various incarnations

# the idea is to separate the plotting of the overlay from the
# determination of what maps to use

# lofarhdu must be a flattened (2D) LOFAR map. opthdu can be any type
# of optical map. rms_use must be the local rms

from time import sleep
import numpy as np
successful=False
while not successful:
    try:
        import aplpy
        successful=True
    except:
        sleep(np.random.rand()*20)
import matplotlib.pyplot as plt
from astropy.wcs import WCS
from astropy.table import Table

def find_noise(a):
    b=a.flatten()
    for i in range(10):
        m=np.nanmean(b)
        s=np.nanstd(b)
        b=b[b<(m+5.0*s)]
    return m,s

def find_noise_area(hdu,ra,dec,size,channel=0):
    # ra, dec, size in degrees
    if len(hdu[0].data.shape)==2:
        cube=False
        ysize,xsize=hdu[0].data.shape
    else:
        channels,ysize,xsize=hdu[0].data.shape
        cube=True
    w=WCS(hdu[0].header)
    ras=[ra-size,ra-size,ra+size,ra+size]
    decs=[dec-size,dec+size,dec-size,dec+size]
    xv=[]
    yv=[]
    for r,d in zip(ras,decs):
        if cube:
            x,y,c=w.wcs_world2pix(r,d,0,0)
        else:
            x,y=w.wcs_world2pix(r,d,0)
        xv.append(x)
        yv.append(y)
    xmin=int(min(xv))
    if xmin<0: xmin=0
    xmax=int(max(xv))
    if xmax>=xsize: xmax=xsize-1
    ymin=int(min(yv))
    if ymin<0: ymin=0
    ymax=int(max(yv))
    if ymax>=ysize: ymax=ysize-1
    #print xmin,xmax,ymin,ymax
    if cube:
        subim=hdu[0].data[channel,ymin:ymax,xmin:xmax]
    else:
        subim=hdu[0].data[ymin:ymax,xmin:xmax]
    mean,noise=find_noise(subim)
    for i in range(5,0,-1):
        vmax=np.nanmedian(subim[subim>(mean+i*noise)])
        if not(np.isnan(vmax)):
            break
    return mean,noise,vmax

def show_overlay(lofarhdu,opthdu,ra,dec,size,firsthdu=None,vlasshdu=None,rms_use=None,bmaj=None,bmin=None,bpa=None,title=None,save_name=None,plotpos=None,block=True,interactive=False,plot_coords=True,overlay_cat=None,lw=1.0,show_lofar=True,no_labels=False,show_grid=True,overlay_region=None,overlay_scale=1.0,circle_radius=None,coords_color='white',coords_lw=1,coords_ra=None,coords_dec=None,marker_ra=None,marker_dec=None,marker_color='white',marker_lw=3,noisethresh=1,lofarlevel=2.0,first_color='lightgreen',vlass_color='salmon',drlimit=500,interactive_handler=None,peak=None,ellipse_color='red',lw_ellipse=3,ellipse_style='solid'):
    '''
    show_overlay: make an overlay using AplPY.
    lofarhdu: the LOFAR cutout to use for contours
    opthdu: the optical image to use (may be 2D image or RGB cube)
    ra, dec: position to use, in degrees
    size: size in arcseconds
    firsthdu: FIRST cutout to use for contours or None if not required
    vlasshdu: VLASS cutout to use for contours or None if not required
    rms_use: Use a particular LOFAR rms or None to compute it from cutout
    bmaj, bmin, bpa: Beam sizes to use or None to take from the headers
    title: title at the top of the plot or None for no title
    save_name: filename to save image as
    plotpos: list of RA, Dec to plot as markers
    block: if True, wait before exiting if not saving an image
    interactive: if True, allow interaction with the image
    plot_coords: plot a set of co-ordinates as a large cross
    overlay_cat: plot a catalogue (astropy Table) as a set of ellipses with BMaj, BMin, BPA, or None to disable
    lw: line width for contours in Matplotlib units
    show_lofar: if True, show the LOFAR contours
    no_labels: if True, don't produce co-ordinate labels
    show_grid: if True, show a co-ordinate grid
    overlay_region: overlay a ds9-style region if not None
    overlay_scale: scaling factor for catalogue in overlay_cat
    circle_radius: if not None, draw a circle of this radius around the image centre
    coords_color: colour for plot_coords
    coords_lw: line width for plot_coords
    coords_ra, coords_dec: use these co-ordinates for plot_coords
    marker_ra, marker_dec: old marker list specification; deprecated, use plotpos instead
    marker_color,marker_lw: attributes for markers
    noisethresh: scaling noise for the optical images (lower cutoff at mean + rms*noisethresh)
    lofarlevel: lowest LOFAR contour (units sigma)
    first_color: colour for FIRST contours
    vlass_color: colour for VLASS contours
    drlimit: dynamic range limit for LOFAR data
    interactive_handler: function to call for clicks on an interactive map
    peak: use this LOFAR flux density as the peak value; if None, calculate from the map
    ellipse_color: colour for the ellipses in overlay_cat: either a string or a list with entries for each ellipse
    lw_ellipse: line width for the ellipses; either a string or a list with entries for each ellipse
    ellipse_style: line style for the ellipses; either a string or a list with entries for each ellipse

    '''
    if lofarhdu is None:
        print 'LOFAR HDU is missing, not showing it'
        show_lofar=False
    try:
        from matplotlib.cbook import MatplotlibDeprecationWarning
        import warnings
        warnings.simplefilter('ignore', MatplotlibDeprecationWarning)
    except:
        print 'Cannot hide warnings'

    print '========== Doing overlay at',ra,dec,'with size',size,'==========='
    print '========== Title is',title,'=========='    
    
    if coords_ra is None:
        coords_ra=ra
        coords_dec=dec

    if show_lofar:
        if peak is None:
            lofarmax=np.nanmax(lofarhdu[0].data)
        else:
            print 'Using user-specified peak flux of',peak
            lofarmax=peak
        if rms_use is None:
            rms_use=find_noise_area(lofarhdu,ra,dec,size)[1]
            print 'Using LOFAR rms',rms_use
        print lofarmax/drlimit,rms_use*lofarlevel
        minlevel=max([lofarmax/drlimit,rms_use*lofarlevel])
        levels=minlevel*2.0**np.linspace(0,14,30)

    hdu=opthdu

    if len(hdu[0].data.shape)>2:
        # This is an RGB image. Try to do something sensible with it
        vmins=[]
        for i in range(3):
            mean,noise,vmax=find_noise_area(hdu,ra,dec,size,channel=i)
            vmin=mean+noisethresh*noise
            vmins.append(vmin)
        aplpy.make_rgb_image(hdu.filename(),'rgb.png',stretch_r='log',stretch_g='log',stretch_b='log',vmin_r=vmins[0],vmin_g=vmins[1],vmin_b=vmins[2]) # FILENAME NOT SAFE
        f=aplpy.FITSFigure('rgb.png',north=True)
        print 'centring on',ra,dec,size
        f.recenter(ra,dec,width=size,height=size)
        f.show_rgb()
       
        
    else:
        print 'I do not want to be here'
        mean,noise,vmax=find_noise_area(hdu,ra,dec,size)
        print 'Optical parameters are',mean,noise,vmax
        f = aplpy.FITSFigure(hdu,north=True)
        print 'centring on',ra,dec,size
        f.recenter(ra,dec,width=size,height=size)
        f.show_colorscale(vmin=mean+noisethresh*noise,vmax=vmax,stretch='log')

    if bmaj is not None:
        f._header['BMAJ']=bmaj
        f._header['BMIN']=bmin
        f._header['BPA']=bpa

    if show_lofar: f.show_contour(lofarhdu,colors='yellow',linewidths=lw, levels=levels)

    if firsthdu is not None:
        firstrms=find_noise_area(firsthdu,ra,dec,size)[1]
        print 'Using FIRST rms',firstrms
        firstlevels=firstrms*3*2.0**np.linspace(0,14,30)
        f.show_contour(firsthdu,colors=first_color,linewidths=lw, levels=firstlevels)

    if vlasshdu is not None:
        vlassrms=find_noise_area(vlasshdu,ra,dec,size)[1]
        print 'Using VLASS rms',vlassrms
        vlasslevels=vlassrms*3*2.0**np.linspace(0,14,30)
        f.show_contour(vlasshdu,colors=vlass_color,linewidths=lw, levels=vlasslevels)

    if bmaj is not None:
        f.add_beam()
        f.beam.set_corner('bottom left')
        f.beam.set_edgecolor('red')
        f.beam.set_facecolor('white')

    if plot_coords:
        f.show_markers(coords_ra,coords_dec,marker='+',facecolor=coords_color,edgecolor=coords_color,linewidth=coords_lw,s=1500,zorder=100)

    if marker_ra is not None:
        f.show_markers(marker_ra,marker_dec,marker='x',facecolor=marker_color,edgecolor=marker_color,linewidth=marker_lw,s=1500,zorder=100)
        

    if plotpos is not None:
        if not isinstance(plotpos,list):
            plotpos=[(plotpos,'x'),]
        for element in plotpos:
            # if a colour is specified assume it's for a filled shape and unfill it
            if len(element)==3:
                t,marker,edgecolor=element
                facecolor='None'
            else:
                t,marker=element
                edgecolor='white'
                facecolor=edgecolor
            if len(t)>0:
                f.show_markers(t['ra'],t['dec'],marker=marker,facecolor=facecolor,edgecolor=edgecolor,linewidth=2,s=750,zorder=100)

    if circle_radius is not None:
        f.show_circles([ra,],[dec,],[circle_radius,],facecolor='none',edgecolor='cyan',linewidth=5)

    if overlay_cat is not None:
        t=overlay_cat
        f.show_ellipses(t['RA'],t['DEC'],t['Maj']*2/overlay_scale,t['Min']*2/overlay_scale,angle=90+t['PA'],edgecolor=ellipse_color,linewidth=lw_ellipse,linestyle=ellipse_style,zorder=100)

    if overlay_region is not None:
        f.show_regions(overlay_region)

    if no_labels:
        f.axis_labels.hide()
        f.tick_labels.hide()
    if show_grid:
        f.add_grid()
        f.grid.show()
        f.grid.set_xspacing(1.0/60.0)
        f.grid.set_yspacing(1.0/60.0)

    if title is not None:
        plt.title(title)
    plt.tight_layout()
    if save_name is None:
        plt.show(block=block)
    else:
        plt.savefig(save_name)

    def onclick(event):
        xp=event.xdata
        yp=event.ydata
        xw,yw=f.pixel2world(xp,yp)
        if event.button==2:
            print title,xw,yw

    if interactive:
        fig=plt.gcf()
        if interactive_handler is None:
            cid = fig.canvas.mpl_connect('button_press_event', onclick)
        else:
            I=interactive_handler(f)
            fig.canvas.mpl_connect('button_press_event', I.onclick)
    return f

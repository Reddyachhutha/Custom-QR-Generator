from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    SquareModuleDrawer,
    CircleModuleDrawer,
    RoundedModuleDrawer,
    GappedSquareModuleDrawer
)
from qrcode.image.styles.colormasks import SolidFillColorMask, ImageColorMask
from PIL import Image, ImageEnhance, ImageDraw
import io

app = FastAPI(title="Customized QR Generator API")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=b"", media_type="image/x-icon")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate")
async def generate_qr(
    url: str = Form(...),
    shape: str = Form("square"),
    fill_color: str = Form("#000000"),
    back_color: str = Form("#ffffff"),
    logo: UploadFile = File(None),
    logo_size_factor: float = Form(0.28),
    logo_shape: str = Form("square"),
    logo_position: str = Form("center"),
    bg_image: UploadFile = File(None)
):
    try:
        # High error correction is necessary to embed logos
        # Increase minimum version if logo is provided to ensure enough data redundancy
        min_version = 6 if logo else 1
        qr = qrcode.QRCode(
            version=min_version,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Select module drawer based on user shape preference
        if shape == "circle":
            module_drawer = CircleModuleDrawer()
        elif shape == "rounded":
            module_drawer = RoundedModuleDrawer()
        elif shape == "gapped_square":
            module_drawer = GappedSquareModuleDrawer()
        else:
            module_drawer = SquareModuleDrawer()

        # Handle colors
        def hex_to_rgb(hex_code):
            hex_code = hex_code.lstrip('#')
            return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

        fill_rgb = hex_to_rgb(fill_color)
        back_rgb = hex_to_rgb(back_color)
        
        color_mask = SolidFillColorMask(back_color=back_rgb, front_color=fill_rgb)
        
        make_image_kwargs = {
            "image_factory": StyledPilImage,
            "module_drawer": module_drawer,
            "color_mask": color_mask
        }
        
        # We ALWAYS generate the QR code with a transparent background first
        make_image_kwargs["color_mask"] = SolidFillColorMask(
            back_color=(255, 255, 255, 0), # Transparent background
            front_color=(fill_rgb[0], fill_rgb[1], fill_rgb[2], 255)
        )
        img = qr.make_image(**make_image_kwargs).convert("RGBA")
        
        # If background image is provided, it becomes the background behind the dots
        if bg_image:
            bg_bytes = await bg_image.read()
            bg_pil = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
            bg_pil = bg_pil.resize(img.size, Image.Resampling.LANCZOS)
            
            # Smart Contrast Adjustment
            fill_lum = 0.299 * fill_rgb[0] + 0.587 * fill_rgb[1] + 0.114 * fill_rgb[2]
            enhancer = ImageEnhance.Brightness(bg_pil)
            if fill_lum > 128:
                bg_pil = enhancer.enhance(0.4) # Light dots -> Darken bg image
            else:
                bg_pil = enhancer.enhance(1.6) # Dark dots -> Lighten bg image
                
            # Composite QR code (dots) OVER the background image
            final_img = Image.alpha_composite(bg_pil, img)
            img = final_img
        else:
            # If no image, just put the selected background color behind it
            solid_bg = Image.new("RGBA", img.size, (back_rgb[0], back_rgb[1], back_rgb[2], 255))
            img = Image.alpha_composite(solid_bg, img)
            
        # --- FIX: Guarantee Solid Finder Patterns (Eyes) for Scannability ---
        img_solid = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            color_mask=SolidFillColorMask(back_color=back_rgb, front_color=fill_rgb)
        ).convert("RGBA")
        
        modules_count = len(qr.modules)
        box_size = qr.box_size
        border = qr.border
        eye_pixel_size = 7 * box_size
        
        tl = (border * box_size, border * box_size)
        tr = ((border + modules_count - 7) * box_size, border * box_size)
        bl = (border * box_size, (border + modules_count - 7) * box_size)
        
        for coords in [tl, tr, bl]:
            box = (coords[0], coords[1], coords[0] + eye_pixel_size, coords[1] + eye_pixel_size)
            img.paste(img_solid.crop(box), box)
        # --------------------------------------------------------------------
        
        # If logo is provided, paste it on the code
        if logo:
            logo_bytes = await logo.read()
            logo_pil = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            
            img_w, img_h = img.size
            logo_sz = int(img_w * logo_size_factor)
            
            # Crop logo to square
            lw, lh = logo_pil.size
            min_dim = min(lw, lh)
            left = int((lw - min_dim) / 2)
            top = int((lh - min_dim) / 2)
            right = int((lw + min_dim) / 2)
            bottom = int((lh + min_dim) / 2)
            logo_pil = logo_pil.crop((left, top, right, bottom))
            logo_pil = logo_pil.resize((logo_sz, logo_sz), Image.Resampling.LANCZOS)
            
            # Apply shape mask if needed
            if logo_shape == "circle":
                mask = Image.new('L', (logo_sz, logo_sz), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, logo_sz, logo_sz), fill=255)
                logo_pil.putalpha(mask)
                
            # Determine position
            if logo_position == "top":
                pos_x = (img_w - logo_sz) // 2
                pos_y = border * box_size
            elif logo_position == "bottom":
                pos_x = (img_w - logo_sz) // 2
                pos_y = img_h - (border * box_size) - logo_sz
            else: # center
                pos_x = (img_w - logo_sz) // 2
                pos_y = (img_h - logo_sz) // 2
            
            pos = (pos_x, pos_y)
            
            # Add a white background behind the logo to ensure the code lines don't obscure it
            if logo_shape == "circle":
                logo_bg = Image.new("RGBA", (logo_sz + 10, logo_sz + 10), (255, 255, 255, 0))
                draw_bg = ImageDraw.Draw(logo_bg)
                draw_bg.ellipse((0, 0, logo_sz+10, logo_sz+10), fill="white")
                img.paste(logo_bg, (pos_x - 5, pos_y - 5), logo_bg)
            else:
                logo_bg = Image.new("RGBA", (logo_sz + 10, logo_sz + 10), "white")
                img.paste(logo_bg, (pos_x - 5, pos_y - 5), logo_bg)
                
            img.paste(logo_pil, pos, logo_pil)

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        return Response(content=img_byte_arr, media_type="image/png")
    except Exception as e:
        print(f"Error generating QR code: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Mount the frontend directory to serve HTML, CSS, JS directly
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

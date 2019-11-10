"""Provide sample helpers."""


def next_well_xy(sample, plate_name, x_wells=12, y_wells=8):
    """Return the next not done well for the given plate x, y format."""
    plate = sample.get_plate(plate_name)
    if plate is None:
        return None, None
    done = {
        (well_x, well_y): well
        for (well_x, well_y), well in plate.wells.items()
        if well.img_ok
    }
    x_well, y_well = next(
        (
            (x_well, y_well)
            for x_well in range(x_wells)
            for y_well in range(y_wells)
            if (x_well, y_well) not in done
        ),
        (None, None),
    )
    return x_well, y_well

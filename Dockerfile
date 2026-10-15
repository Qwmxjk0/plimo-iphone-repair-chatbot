FROM nginx:1.31.6-alpine
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
# Cache busting: pages reference code as ?v=<content hash>, so a deploy never leaves old JS/CSS in browsers.
RUN cd /usr/share/nginx/html && v=$(cat *.js *.css | md5sum | cut -c1-10) \
 && sed -i -E "s/(src|href)=\"([a-z]+)\.(js|css)\"/\1=\"\2.\3?v=$v\"/g" *.html
EXPOSE 80
